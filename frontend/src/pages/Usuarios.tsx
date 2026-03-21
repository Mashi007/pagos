Ã¯Â»Â¿Ã¯Â»Â¿import { useState, useEffect, useCallback } from 'react'
import { Users, Plus, Search, Edit, Trash2, Shield, Mail, UserCheck, UserX, Loader2, RefreshCw, X, Save } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Badge } from '../components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'
import { PasswordField } from '../components/ui/PasswordField'
import { usePassword } from '../hooks/usePassword'
import { userService, User, UserCreate } from '../services/userService'
import { useSimpleAuth } from '../store/simpleAuthStore'
import { clearAuthStorage } from '../utils/storage'
import { toast } from 'sonner'
import { getErrorMessage, getErrorDetail } from '../types/errors'
import { logger } from '../utils/logger'
import { BASE_PATH } from '../config/env'

export function Usuarios() {
  const { user: currentUser } = useSimpleAuth()
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
    rol: 'operativo',  // Cambio clave: rol ÃÂ¢Ã¢ÂÂ Ã¢ÂÂ is_admin
    password: '',
    cargo: 'Usuario', // Valor por defecto para evitar error de NOT NULL
    is_active: true
  })

  // Hook para validar contraseÃÂ±a
  const { validatePassword } = usePassword()

  // Cargar usuarios al montar el componente
  useEffect(() => {
    cargarUsuarios()
  }, [])

  // Cerrar modal con tecla Escape
  useEffect(() => {
    if (!showCreateForm) return

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleCloseForm()
      }
    }

    document.addEventListener('keydown', handleEscape)
    // Prevenir scroll del body cuando el modal estÃÂ¡ abierto
    document.body.style.overflow = 'hidden'

    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = 'unset'
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showCreateForm])

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
        logger.warn('Respuesta sin items vÃÂ¡lidos', { response })
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
      // Confirmar eliminaciÃÂ³n permanente
      const confirmar = window.confirm(
        'ÃÂ¢ÃÂ¡ ÃÂ¯ÃÂ¸ÃÂ ÃÂ¿EstÃÂ¡s seguro de que quieres ELIMINAR PERMANENTEMENTE este usuario?\n\n' +
        'Esta acciÃÂ³n NO se puede deshacer y el usuario serÃÂ¡ borrado completamente de la base de datos.'
      )

      if (!confirmar) {
        return
      }

      await userService.eliminarUsuario(id)
      logger.userAction('eliminar_usuario', { userId: id })
      toast.success('ÃÂ¢ÃÂÃ¢ÂÂ¦ Usuario eliminado PERMANENTEMENTE de la base de datos')
      cargarUsuarios() // Recargar lista
    } catch (err) {
      logger.apiError(`/api/v1/usuarios/${id}`, err, { action: 'eliminarUsuario', userId: id })
      toast.error('ÃÂ¢ÃÂÃÂ Error al eliminar usuario permanentemente')
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
      rol: usuario.rol || 'operativo',  // Cambio clave: rol ÃÂ¢Ã¢ÂÂ Ã¢ÂÂ is_admin
      password: '',
      cargo: usuario.cargo || '', // Si es null, usar string vacÃÂ­o (no 'Usuario')
      is_active: usuario.is_active
    })
    setShowCreateForm(true)
  }

  // ValidaciÃÂ³n del formulario
  const isFormValid = () => {
    if (!formData.email || !formData.nombre || !formData.apellido) {
      return false
    }

    // Si estamos creando un nuevo usuario, la contraseÃÂ±a es obligatoria
    if (!editingUsuario && !formData.password) {
      return false
    }

    // Si hay una contraseÃÂ±a (ya sea en creaciÃÂ³n o actualizaciÃÂ³n), debe cumplir todos los requisitos
    if (formData.password && formData.password.trim() !== '') {
      const passwordValidation = validatePassword(formData.password)
      if (!passwordValidation.isValid) {
        return false
      }
    }

    return true
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validar formulario antes de enviar
    if (!isFormValid()) {
      toast.error('Por favor completa todos los campos requeridos y asegÃÂºrate de que la contraseÃÂ±a cumpla con todos los requisitos')
      return
    }

    try {
      setIsSubmitting(true)

      if (editingUsuario) {
        // Actualizar usuario existente - construir UserUpdate correctamente
        // IMPORTANTE: Incluir todos los campos que queremos actualizar, incluso si no cambiaron
        // El backend usa exclude_unset=True, asÃÂ­ que necesitamos enviar valores explÃÂ­citos
        // ÃÂ¢ÃÂÃ¢ÂÂ¦ CRÃÂTICO: Siempre incluir is_admin explÃÂ­citamente, incluso si es False
        const updateData: any = {
          email: formData.email,
          nombre: formData.nombre,
          apellido: formData.apellido,
          rol: formData.rol,
          is_active: formData.is_active,
        }

        // ÃÂ¢ÃÂÃ¢ÂÂ¦ CRÃÂTICO: Validar que editingUsuario.id existe y es vÃÂ¡lido
        if (!editingUsuario || !editingUsuario.id) {
          console.error('ÃÂ¢ÃÂÃÂ [Usuarios] ERROR: editingUsuario o editingUsuario.id es invÃÂ¡lido:', editingUsuario)
          toast.error('Error: Usuario a editar no vÃÂ¡lido')
          return
        }

        // ÃÂ¢ÃÂÃ¢ÂÂ¦ CRÃÂTICO: Logging detallado del usuario que se estÃÂ¡ actualizando
        console.log('ÃÂ°ÃÂ¸Ã¢ÂÂÃÂ¤ [Usuarios] Enviando actualizaciÃÂ³n:', {
          userId: editingUsuario.id,
          email: editingUsuario.email,
          nombre: editingUsuario.nombre,
          apellido: editingUsuario.apellido,
        })

        // Incluir cargo del formulario (valor que el usuario estÃÂ¡ editando)
        // Si el cargo estÃÂ¡ vacÃÂ­o o solo tiene espacios, enviar null para limpiar el campo
        if (formData.cargo && formData.cargo.trim() !== '') {
          updateData.cargo = formData.cargo.trim()
        } else {
          // Si estÃÂ¡ vacÃÂ­o, enviar null para que se limpie en la BD
          updateData.cargo = null
        }

        // Incluir password solo si se proporcionÃÂ³ uno nuevo (no vacÃÂ­o)
        // Si estÃÂ¡ vacÃÂ­o, NO lo incluimos para que el backend no intente actualizarlo
        const passwordChanged = formData.password && formData.password.trim() !== ''
        if (passwordChanged) {
          updateData.password = formData.password.trim()
        }

        const updatedUser = await userService.actualizarUsuario(editingUsuario.id, updateData)

        // ÃÂ¢ÃÂÃ¢ÂÂ¦ Si se cambiÃÂ³ la contraseÃÂ±a del usuario actual, forzar logout y redirigir al login
        if (passwordChanged && currentUser && editingUsuario.id === currentUser.id) {
          toast.success('ContraseÃÂ±a cambiada exitosamente. Debes volver a iniciar sesiÃÂ³n.')
          // Limpiar sesiÃÂ³n y redirigir al login
          clearAuthStorage()
          setTimeout(() => {
            window.location.href = BASE_PATH + '/login'
          }, 1000)
        } else {
          toast.success('Usuario actualizado exitosamente')
          // Actualizar lista en local para evitar GET extra que podrÃÂ­a 401 y redirigir al login
          setUsuarios(prev => prev.map(u => u.id === editingUsuario.id ? updatedUser : u))
        }
      } else {
        // Crear nuevo usuario
        const createData: any = {
          email: formData.email,
          nombre: formData.nombre,
          apellido: formData.apellido,
          rol: formData.rol,
          is_active: formData.is_active,
          password: formData.password,
        }

        // Incluir cargo solo si tiene valor (no vacÃÂ­o)
        if (formData.cargo && formData.cargo.trim() !== '') {
          createData.cargo = formData.cargo.trim()
        }
        // Si estÃÂ¡ vacÃÂ­o, no incluirlo (serÃÂ¡ null en la BD)

        const newUser = await userService.crearUsuario(createData)
        toast.success('Usuario creado exitosamente')
        // AÃÂ±adir a la lista en local para evitar GET extra que podrÃÂ­a 401 y redirigir al login
        setUsuarios(prev => [...prev, newUser])
      }

      setShowCreateForm(false)
      setEditingUsuario(null)
      resetForm()
      logger.userAction(editingUsuario ? 'actualizar_usuario' : 'crear_usuario', {
        userId: editingUsuario?.id,
        email: formData.email
      })
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
      rol: 'operativo',  // Cambio clave: rol ÃÂ¢Ã¢ÂÂ Ã¢ÂÂ is_admin
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

  // Filtrar usuarios por tÃÂ©rmino de bÃÂºsqueda
  const usuariosFiltrados = usuarios.filter(usuario =>
    (usuario.nombre && usuario.nombre.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (usuario.apellido && usuario.apellido.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (usuario.email && usuario.email.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  const getRoleBadgeColor = (rol: string) => {  // Cambio clave: rol ÃÂ¢Ã¢ÂÂ Ã¢ÂÂ is_admin
    return rol === 'administrador' ? 'bg-red-600' : 'bg-blue-600'  // Cambio clave: rol ÃÂ¢Ã¢ÂÂ Ã¢ÂÂ is_admin
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Usuarios del Sistema</h1>
          <p className="text-gray-500 mt-1">
            GestiÃÂ³n de usuarios y control de acceso
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
                  {usuarios.filter(u => (u.rol || 'operativo') === 'administrador').length}  {/* Cambio clave: rol ÃÂ¢Ã¢ÂÂ Ã¢ÂÂ is_admin */}
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
                <p className="text-sm text-gray-500">ÃÂltimo Mes</p>
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

      {/* BÃÂºsqueda */}
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
                <TableHead>ÃÂltimo Acceso</TableHead>
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
                      <Badge className={getRoleBadgeColor(usuario.rol || 'operativo')}>  {/* Cambio clave: rol ÃÂ¢Ã¢ÂÂ Ã¢ÂÂ is_admin */}
                        {(usuario.rol || 'operativo') === 'administrador' ? 'Administrador' : 'Operativo'}  {/* Cambio clave: rol ÃÂ¢Ã¢ÂÂ Ã¢ÂÂ is_admin */}
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
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          onClick={handleCloseForm}
        >
          <div
            className="bg-white rounded-lg w-full max-w-md flex flex-col max-h-[90vh] shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header fijo */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200 flex-shrink-0">
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

            {/* Contenido con scroll */}
            <form onSubmit={handleSubmit} className="flex flex-col flex-1 min-h-0">
              <div className="overflow-y-auto p-6 space-y-4 flex-1">
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
                <label htmlFor="rol" className="block text-sm font-medium text-gray-700">Nivel de usuario</label>
                <Select
                  value={formData.rol || 'operativo'}
                  onValueChange={(value: 'administrador' | 'operativo') => setFormData({ ...formData, rol: value })}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="operativo">Operativo</SelectItem>
                    <SelectItem value="administrador">Administrador</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label htmlFor="cargo" className="block text-sm font-medium text-gray-700">Cargo</label>
                <Input
                  id="cargo"
                  value={formData.cargo || ''}
                  onChange={(e) => setFormData({ ...formData, cargo: e.target.value })}
                  placeholder="Ej: Gerente, Analista, Supervisor..."
                  className="mt-1"
                />
                <p className="text-xs text-gray-500 mt-1">Dejar vacÃÂ­o para "Sin especificar"</p>
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                  ContraseÃÂ±a {editingUsuario && '(dejar vacÃÂ­o para mantener la actual)'}
                </label>
                <PasswordField
                  value={formData.password}
                  onChange={(password) => setFormData({ ...formData, password })}
                  placeholder={editingUsuario ? 'Nueva contraseÃÂ±a (opcional)' : 'MÃÂ­nimo 8 caracteres'}
                  required={!editingUsuario}
                  showGenerateButton={true}  // ÃÂ¢ÃÂÃ¢ÂÂ¦ SIEMPRE mostrar botÃÂ³n de generar
                  showCopyButton={true}      // ÃÂ¢ÃÂÃ¢ÂÂ¦ SIEMPRE mostrar botÃÂ³n de copiar
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
              </div>

              {/* Footer fijo con botones */}
              <div className="flex justify-end space-x-2 p-6 border-t border-gray-200 bg-gray-50 flex-shrink-0">
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
                  disabled={isSubmitting || !isFormValid()}
                  className="flex items-center gap-2 disabled:bg-gray-400 disabled:cursor-not-allowed"
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

export default Usuarios

