import { useState, useEffect } from 'react'
import { Users, Plus, Search, Edit, Trash2, Shield, Mail, UserCheck, UserX, Loader2, RefreshCw, X, Save } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { usuarioService, Usuario, UsuarioCreate } from '@/services/usuarioService'
import { toast } from 'sonner'

export function Usuarios() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingUsuario, setEditingUsuario] = useState<Usuario | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  const [formData, setFormData] = useState<UsuarioCreate>({
    email: '',
    nombre: '',
    apellido: '',
    rol: 'USER',
    password: '',
    is_active: true
  })

  // Cargar usuarios al montar el componente
  useEffect(() => {
    cargarUsuarios()
  }, [])

  const cargarUsuarios = async () => {
    try {
      setLoading(true)
      setError(null)
      console.log('🔄 Actualizando usuarios...')
      console.log('📡 Llamando a API: /api/v1/users')
      
      const response = await usuarioService.listarUsuarios({ limit: 100 })
      console.log('✅ Respuesta API recibida:', response)
      console.log('📊 Total usuarios:', response.total)
      console.log('📋 Items recibidos:', response.items?.length || 0)
      
      if (response.items && Array.isArray(response.items)) {
        setUsuarios(response.items)
        console.log('✅ Usuarios cargados exitosamente:', response.items.length)
      } else {
        console.warn('⚠️ Respuesta sin items válidos:', response)
        setUsuarios([])
      }
    } catch (err) {
      console.error('❌ Error API:', err)
      setError('Error al cargar usuarios')
      toast.error('Error al cargar usuarios')
      setUsuarios([])
    } finally {
      setLoading(false)
    }
  }

  const handleEliminar = async (id: number) => {
    try {
      // Confirmar eliminación permanente
      const confirmar = window.confirm(
        '⚠️ ¿Estás seguro de que quieres ELIMINAR PERMANENTEMENTE este usuario?\n\n' +
        'Esta acción NO se puede deshacer y el usuario será borrado completamente de la base de datos.'
      )
      
      if (!confirmar) {
        return
      }
      
      await usuarioService.eliminarUsuario(id)
      toast.success('✅ Usuario eliminado PERMANENTEMENTE de la base de datos')
      cargarUsuarios() // Recargar lista
    } catch (err) {
      toast.error('❌ Error al eliminar usuario permanentemente')
      console.error('Error:', err)
    }
  }

  const handleToggleActivo = async (usuario: Usuario) => {
    try {
      await usuarioService.toggleActivo(usuario.id, !usuario.is_active)
      toast.success(`Usuario ${usuario.is_active ? 'desactivado' : 'activado'} exitosamente`)
      cargarUsuarios() // Recargar lista
    } catch (err) {
      toast.error('Error al cambiar estado del usuario')
      console.error('Error:', err)
    }
  }

  const handleEdit = (usuario: Usuario) => {
    setEditingUsuario(usuario)
    setFormData({
      email: usuario.email,
      nombre: usuario.nombre,
      apellido: usuario.apellido,
      rol: usuario.rol,
      password: '',
      is_active: usuario.is_active
    })
    setShowCreateForm(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    try {
      setIsSubmitting(true)
      
      if (editingUsuario) {
        // Actualizar usuario existente
        await usuarioService.actualizarUsuario(editingUsuario.id, formData)
        toast.success('Usuario actualizado exitosamente')
      } else {
        // Crear nuevo usuario
        await usuarioService.crearUsuario(formData)
        toast.success('Usuario creado exitosamente')
      }
      
      setShowCreateForm(false)
      setEditingUsuario(null)
      resetForm()
      cargarUsuarios()
    } catch (err: any) {
      console.error('Error guardando usuario:', err)
      toast.error(err.response?.data?.detail || 'Error al guardar usuario')
    } finally {
      setIsSubmitting(false)
    }
  }

  const resetForm = () => {
    setFormData({
      email: '',
      nombre: '',
      apellido: '',
      rol: 'USER',
      password: '',
      is_active: true
    })
  }

  const handleCloseForm = () => {
    setShowCreateForm(false)
    setEditingUsuario(null)
    resetForm()
  }

  // Filtrar usuarios por término de búsqueda
  const usuariosFiltrados = usuarios.filter(usuario =>
    usuario.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
    usuario.apellido.toLowerCase().includes(searchTerm.toLowerCase()) ||
    usuario.email.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const getRoleBadgeColor = (rol: string) => {
    const colors: any = {
      'USER': 'bg-blue-600',
      'ADMIN': 'bg-red-600',
      'GERENTE': 'bg-purple-600',
      'COBRANZAS': 'bg-orange-600',
    }
    return colors[rol] || 'bg-gray-600'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Usuarios del Sistema</h1>
          <p className="text-gray-500 mt-1">
            Gestión de usuarios y control de acceso
          </p>
        </div>
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            onClick={cargarUsuarios}
            disabled={loading}
            className="flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
          <Button onClick={() => setShowCreateForm(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Nuevo Usuario
          </Button>
        </div>
      </div>

      {/* Stats Dashboard */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Usuarios</p>
                <p className="text-2xl font-bold">{usuarios.length}</p>
                <p className="text-xs text-gray-400 mt-1">
                  {usuarios.length > 0 ? `${((usuarios.filter(u => u.is_active).length / usuarios.length) * 100).toFixed(1)}% activos` : 'Conectando con BD...'}
                </p>
              </div>
              <Users className="w-8 h-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Activos</p>
                <p className="text-2xl font-bold text-green-600">
                  {usuarios.filter(u => u.is_active).length}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  {loading ? 'Cargando...' : 'Pueden acceder al sistema'}
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
                <p className="text-sm text-gray-500">Administradores</p>
                <p className="text-2xl font-bold text-red-600">
                  {usuarios.filter(u => u.rol === 'ADMIN').length}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  {loading ? 'Cargando...' : 'Pueden crear usuarios'}
                </p>
              </div>
              <Shield className="w-8 h-8 text-red-600" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Último Mes</p>
                <p className="text-2xl font-bold text-blue-600">
                  {usuarios.filter(u => {
                    const fechaCreacion = new Date(u.created_at)
                    const haceUnMes = new Date()
                    haceUnMes.setMonth(haceUnMes.getMonth() - 1)
                    return fechaCreacion >= haceUnMes
                  }).length}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  {loading ? 'Cargando...' : 'Usuarios agregados'}
                </p>
              </div>
              <Plus className="w-8 h-8 text-blue-600" />
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
              placeholder="Buscar usuario por nombre o email..."
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
                <TableHead>Usuario</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Rol</TableHead>
                <TableHead>Cargo</TableHead>
                <TableHead>Último Acceso</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                    <p className="text-gray-500">Cargando usuarios...</p>
                  </TableCell>
                </TableRow>
              ) : error ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    <p className="text-red-500">{error}</p>
                    <Button onClick={cargarUsuarios} className="mt-2">
                      Reintentar
                    </Button>
                  </TableCell>
                </TableRow>
              ) : usuariosFiltrados.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    <p className="text-gray-500">No se encontraron usuarios</p>
                  </TableCell>
                </TableRow>
              ) : (
                usuariosFiltrados.map((usuario) => (
                  <TableRow key={usuario.id}>
                    <TableCell>
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white font-medium">
                          {usuario.nombre.charAt(0)}{usuario.apellido.charAt(0)}
                        </div>
                        <div>
                          <p className="font-medium">{usuario.nombre} {usuario.apellido}</p>
                          <p className="text-xs text-gray-500">ID: {usuario.id}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center text-sm">
                        <Mail className="w-3 h-3 mr-1 text-gray-400" />
                        {usuario.email}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={getRoleBadgeColor(usuario.rol)}>
                        {usuario.rol}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-gray-600">
                      {usuario.cargo || 'Sin especificar'}
                    </TableCell>
                    <TableCell className="text-sm text-gray-600">
                      {usuario.last_login ? (
                        new Date(usuario.last_login).toLocaleDateString('es-VE', {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })
                      ) : (
                        'Nunca'
                      )}
                    </TableCell>
                    <TableCell>
                      {usuario.is_active ? (
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
                          onClick={() => setEditingUsuario(usuario)}
                          title="Editar usuario"
                        >
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={() => handleToggleActivo(usuario)}
                          title={usuario.is_active ? "Desactivar" : "Activar"}
                        >
                          {usuario.is_active ? (
                            <UserX className="w-4 h-4 text-red-600" />
                          ) : (
                            <UserCheck className="w-4 h-4 text-green-600" />
                          )}
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={() => handleEliminar(usuario.id)}
                          title="Eliminar usuario"
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

      {/* Modal de Crear/Editar Usuario */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">
                {editingUsuario ? 'Editar Usuario' : 'Nuevo Usuario'}
              </h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCloseForm}
                className="text-gray-500 hover:text-gray-700"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  required
                  className="mt-1"
                />
              </div>

              <div>
                <Label htmlFor="nombre">Nombre</Label>
                <Input
                  id="nombre"
                  value={formData.nombre}
                  onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                  required
                  className="mt-1"
                />
              </div>

              <div>
                <Label htmlFor="apellido">Apellido</Label>
                <Input
                  id="apellido"
                  value={formData.apellido}
                  onChange={(e) => setFormData({ ...formData, apellido: e.target.value })}
                  required
                  className="mt-1"
                />
              </div>

              <div>
                <Label htmlFor="rol">Rol</Label>
                <Select
                  value={formData.rol}
                  onValueChange={(value) => setFormData({ ...formData, rol: value })}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="USER">Usuario</SelectItem>
                    <SelectItem value="ADMIN">Administrador</SelectItem>
                    <SelectItem value="GERENTE">Gerente</SelectItem>
                    <SelectItem value="COBRANZAS">Cobranzas</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="password">
                  Contraseña {editingUsuario && '(dejar vacío para mantener la actual)'}
                </Label>
                <Input
                  id="password"
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  required={!editingUsuario}
                  className="mt-1"
                />
              </div>

              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="rounded"
                />
                <Label htmlFor="is_active">Usuario activo</Label>
              </div>

              <div className="flex justify-end space-x-2 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleCloseForm}
                  disabled={isSubmitting}
                >
                  Cancelar
                </Button>
                <Button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex items-center gap-2"
                >
                  {isSubmitting ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Save className="w-4 h-4" />
                  )}
                  {editingUsuario ? 'Actualizar' : 'Crear'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

