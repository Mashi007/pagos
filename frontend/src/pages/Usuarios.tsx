import { useState, useEffect } from 'react'
import { Users, Plus, Search, Edit, Trash2, Shield, Mail, UserCheck, UserX, Loader2, RefreshCw, X, Save } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { PasswordField } from '@/components/ui/PasswordField'
import { userService, User, UserCreate } from '@/services/userService'
import { toast } from 'sonner'
import { getErrorMessage, getErrorDetail } from '@/types/errors'
import { logger } from '@/utils/logger'

export function Usuarios() {
  const [usuarios, setUsuarios] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingUsuario, setEditingUsuario] = useState<User | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  const [formData, setFormData] = useState<UserCreate>({
    email: '',
    nombre: '',
    apellido: '',
    is_admin: false,  // Cambio clave: rol → is_admin
    password: '',
    cargo: 'Usuario', // Valor por defecto para evitar error de NOT NULL
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
      logger.debug('Actualizando usuarios', { endpoint: '/api/v1/usuarios' })
      
      const response = await userService.listarUsuarios(1, 100)
      logger.debug('Respuesta API recibida', { 
        total: response.total, 
        itemsCount: response.items?.length || 0 
      })
      
      if (response.items && Array.isArray(response.items)) {
        setUsuarios(response.items)
        logger.debug('Usuarios cargados exitosamente', { count: response.items.length })
      } else {
        logger.warn('Respuesta sin items válidos', { response })
        setUsuarios([])
      }
    } catch (err) {
      logger.apiError('/api/v1/usuarios', err, { action: 'cargarUsuarios' })
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
      
      await userService.eliminarUsuario(id)
      logger.userAction('eliminar_usuario', { userId: id })
      toast.success('✅ Usuario eliminado PERMANENTEMENTE de la base de datos')
      cargarUsuarios() // Recargar lista
    } catch (err) {
      logger.apiError(`/api/v1/usuarios/${id}`, err, { action: 'eliminarUsuario', userId: id })
      toast.error('❌ Error al eliminar usuario permanentemente')
    }
  }

  const handleToggleActivo = async (usuario: User) => {
    try {
      await userService.toggleActivo(usuario.id, !usuario.is_active)
      logger.userAction('toggle_usuario_activo', { 
        userId: usuario.id, 
        nuevoEstado: !usuario.is_active 
      })
      toast.success(`Usuario ${usuario.is_active ? 'desactivado' : 'activado'} exitosamente`)
      cargarUsuarios() // Recargar lista
    } catch (err) {
      logger.apiError(`/api/v1/usuarios/${usuario.id}/toggle`, err, { 
        action: 'toggleActivo', 
        userId: usuario.id 
      })
      toast.error('Error al cambiar estado del usuario')
    }
  }


  const handleEdit = (usuario: User) => {
    setEditingUsuario(usuario)
    setFormData({
      email: usuario.email,
      nombre: usuario.nombre,
      apellido: usuario.apellido,
      is_admin: usuario.is_admin,  // Cambio clave: rol → is_admin
      password: '',
      cargo: usuario.cargo || 'Usuario', // Valor por defecto si no existe
      is_active: usuario.is_active
    })
    setShowCreateForm(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    try {
      setIsSubmitting(true)
      
      if (editingUsuario) {
        // Actualizar usuario existente - construir UserUpdate correctamente
        // IMPORTANTE: Incluir todos los campos que queremos actualizar, incluso si no cambiaron
        // El backend usa exclude_unset=True, así que necesitamos enviar valores explícitos
        const updateData: any = {
          email: formData.email,
          nombre: formData.nombre,
          apellido: formData.apellido,
          is_admin: formData.is_admin,
          is_active: formData.is_active,
        }
        
        // Incluir cargo solo si el usuario original tenía cargo (no el default)
        if (editingUsuario.cargo && editingUsuario.cargo !== 'Usuario') {
          updateData.cargo = editingUsuario.cargo
        }
        
        // Incluir password solo si se proporcionó uno nuevo (no vacío)
        // Si está vacío, NO lo incluimos para que el backend no intente actualizarlo
        if (formData.password && formData.password.trim() !== '') {
          updateData.password = formData.password.trim()
        }
        
        await userService.actualizarUsuario(editingUsuario.id, updateData)
        toast.success('Usuario actualizado exitosamente')
      } else {
        // Crear nuevo usuario
        await userService.crearUsuario(formData)
        toast.success('Usuario creado exitosamente')
      }
      
      setShowCreateForm(false)
      setEditingUsuario(null)
      resetForm()
      logger.userAction(editingUsuario ? 'actualizar_usuario' : 'crear_usuario', {
        userId: editingUsuario?.id,
        email: formData.email
      })
      cargarUsuarios()
    } catch (err: unknown) {
      logger.apiError('/api/v1/usuarios', err, { 
        action: editingUsuario ? 'actualizarUsuario' : 'crearUsuario',
        editing: !!editingUsuario
      })
      const errorMessage = getErrorMessage(err)
      const detail = getErrorDetail(err)
      toast.error(detail || errorMessage || 'Error al guardar usuario')
    } finally {
      setIsSubmitting(false)
    }
  }

  const resetForm = () => {
    setFormData({
      email: '',
      nombre: '',
      apellido: '',
      is_admin: false,  // Cambio clave: rol → is_admin
      password: '',
      cargo: 'Usuario', // Valor por defecto
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
    (usuario.nombre && usuario.nombre.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (usuario.apellido && usuario.apellido.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (usuario.email && usuario.email.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  const getRoleBadgeColor = (is_admin: boolean) => {  // Cambio clave: rol → is_admin
    return is_admin ? 'bg-red-600' : 'bg-blue-600'  // Cambio clave: rol → is_admin
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
                  {usuarios.filter(u => u.is_admin).length}  {/* Cambio clave: rol → is_admin */}
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
                      <Badge className={getRoleBadgeColor(usuario.is_admin)}>  {/* Cambio clave: rol → is_admin */}
                        {usuario.is_admin ? 'Administrador' : 'Usuario'}  {/* Cambio clave: rol → is_admin */}
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
                          onClick={() => handleEdit(usuario)}
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
                <label htmlFor="email" className="block text-sm font-medium text-gray-700">Email</label>
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
                <label htmlFor="nombre" className="block text-sm font-medium text-gray-700">Nombre</label>
                <Input
                  id="nombre"
                  value={formData.nombre}
                  onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                  required
                  className="mt-1"
                />
              </div>

              <div>
                <label htmlFor="apellido" className="block text-sm font-medium text-gray-700">Apellido</label>
                <Input
                  id="apellido"
                  value={formData.apellido}
                  onChange={(e) => setFormData({ ...formData, apellido: e.target.value })}
                  required
                  className="mt-1"
                />
              </div>

              <div>
                <label htmlFor="is_admin" className="block text-sm font-medium text-gray-700">Tipo de Usuario</label>
                <Select
                  value={formData.is_admin ? 'ADMIN' : 'USER'}
                  onValueChange={(value) => setFormData({ ...formData, is_admin: value === 'ADMIN' })}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="USER">Usuario Normal</SelectItem>
                    <SelectItem value="ADMIN">Administrador</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                  Contraseña {editingUsuario && '(dejar vacío para mantener la actual)'}
                </label>
                <PasswordField
                  value={formData.password}
                  onChange={(password) => setFormData({ ...formData, password })}
                  placeholder={editingUsuario ? 'Nueva contraseña (opcional)' : 'Mínimo 8 caracteres'}
                  required={!editingUsuario}
                  showGenerateButton={true}  // ✅ SIEMPRE mostrar botón de generar
                  showCopyButton={true}      // ✅ SIEMPRE mostrar botón de copiar
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
                <label htmlFor="is_active" className="text-sm font-medium text-gray-700">Usuario activo</label>
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

