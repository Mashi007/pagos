// frontend/src/components/configuracion/UsuariosConfig.tsx
import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { 
  Users, 
  Plus, 
  Search, 
  Eye, 
  Edit2, 
  Trash2, 
  UserCheck,
  UserX,
  Shield,
  RefreshCw,
  Save,
  X,
  AlertCircle
} from 'lucide-react'
import { userService, type User, type UserCreate, type UserUpdate } from '@/services/userService'
import { toast } from 'react-hot-toast'

export default function UsuariosConfig() {
  const [usuarios, setUsuarios] = useState<User[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [showViewModal, setShowViewModal] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [viewingUser, setViewingUser] = useState<User | null>(null)
  const [filterActive, setFilterActive] = useState<boolean | undefined>(undefined)

  const [formData, setFormData] = useState<UserCreate>({
    email: '',
    nombre: '',
    apellido: '',
    rol: 'COBRANZAS',
    password: '',
    is_active: true
  })

  const roles = [
    { value: 'ADMINISTRADOR_GENERAL', label: '👑 Administrador General', description: 'Acceso completo al sistema' },
    { value: 'GERENTE', label: '📊 Gerente', description: 'Acceso completo al sistema' },
    { value: 'COBRANZAS', label: '💰 Cobranzas', description: 'Gestión completa excepto editar usuarios y auditoría' }
  ]

  useEffect(() => {
    loadUsuarios()
  }, [filterActive])

  const loadUsuarios = async () => {
    try {
      setLoading(true)
      const data = await userService.listarUsuarios(1, 100, filterActive)
      setUsuarios(data.users)
      setError(null)
    } catch (err: any) {
      console.error('Error al cargar usuarios:', err)
      if (err.response?.status === 503) {
        setError('Servicio temporalmente no disponible. Intenta nuevamente.')
      } else if (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')) {
        setError('Error de conexión. Verifica que el servidor esté funcionando.')
      } else {
        setError('No se pudieron cargar los usuarios.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    try {
      if (editingUser) {
        // Actualizar
        const updateData: UserUpdate = {
          email: formData.email,
          nombre: formData.nombre,
          apellido: formData.apellido,
          rol: formData.rol,
          is_active: formData.is_active
        }
        
        // Solo incluir password si se proporcionó
        if (formData.password) {
          updateData.password = formData.password
        }
        
        await userService.actualizarUsuario(editingUser.id, updateData)
        toast.success('Usuario actualizado exitosamente')
      } else {
        // Crear
        await userService.crearUsuario(formData)
        toast.success('Usuario creado exitosamente')
      }
      
      setShowModal(false)
      resetForm()
      loadUsuarios()
    } catch (err: any) {
      console.error('Error al guardar usuario:', err)
      toast.error(err.response?.data?.detail || 'Error al guardar usuario')
    }
  }

  const handleEdit = (usuario: User) => {
    setEditingUser(usuario)
    setFormData({
      email: usuario.email,
      nombre: usuario.nombre,
      apellido: usuario.apellido,
      rol: usuario.rol,
      password: '', // No pre-llenar password
      is_active: usuario.is_active
    })
    setShowModal(true)
  }

  const handleView = (usuario: User) => {
    setViewingUser(usuario)
    setShowViewModal(true)
  }

  const handleDelete = async (usuario: User) => {
    if (!confirm(`¿Estás seguro de eliminar el usuario ${usuario.full_name || usuario.email}?`)) {
      return
    }
    
    try {
      await userService.eliminarUsuario(usuario.id)
      toast.success('Usuario eliminado exitosamente')
      loadUsuarios()
    } catch (err: any) {
      console.error('Error al eliminar usuario:', err)
      toast.error(err.response?.data?.detail || 'Error al eliminar usuario')
    }
  }

  const resetForm = () => {
    setFormData({
      email: '',
      nombre: '',
      apellido: '',
      rol: 'COBRANZAS',
      password: '',
      is_active: true
    })
    setEditingUser(null)
  }

  const handleCloseModal = () => {
    setShowModal(false)
    resetForm()
  }

  const filteredUsuarios = usuarios.filter(user => 
    user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.apellido.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.rol.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const getRolIcon = (rol: string) => {
    const roleConfig = roles.find(r => r.value === rol)
    return roleConfig?.label.split(' ')[0] || '👤'
  }

  const getRolLabel = (rol: string) => {
    const roleConfig = roles.find(r => r.value === rol)
    return roleConfig?.label || rol
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Users className="h-6 w-6 text-blue-600" />
            Gestión de Usuarios
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Administra usuarios, roles y permisos del sistema
          </p>
        </div>
        <Button
          onClick={() => setShowModal(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white"
        >
          <Plus className="h-4 w-4 mr-2" />
          Nuevo Usuario
        </Button>
      </div>

      {/* Filtros */}
      <Card className="p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input
              placeholder="Buscar por nombre, email o rol..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
          <div className="flex gap-2">
            <Button
              variant={filterActive === undefined ? 'default' : 'outline'}
              onClick={() => setFilterActive(undefined)}
              size="sm"
            >
              Todos ({usuarios.length})
            </Button>
            <Button
              variant={filterActive === true ? 'default' : 'outline'}
              onClick={() => setFilterActive(true)}
              size="sm"
              className="text-green-600"
            >
              <UserCheck className="h-4 w-4 mr-1" />
              Activos
            </Button>
            <Button
              variant={filterActive === false ? 'default' : 'outline'}
              onClick={() => setFilterActive(false)}
              size="sm"
              className="text-red-600"
            >
              <UserX className="h-4 w-4 mr-1" />
              Inactivos
            </Button>
          </div>
          <Button
            variant="outline"
            onClick={loadUsuarios}
            size="sm"
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </Card>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              <span>{error}</span>
            </div>
            <Button 
              onClick={loadUsuarios}
              variant="outline" 
              size="sm"
              className="ml-4"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Reintentar
            </Button>
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="text-center py-8">
          <RefreshCw className="h-8 w-8 animate-spin text-blue-600 mx-auto mb-2" />
          <p className="text-gray-600">Cargando usuarios...</p>
        </div>
      )}

      {/* Tabla de usuarios */}
      {!loading && !error && (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Usuario
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Rol
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Estado
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Último acceso
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Acciones
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredUsuarios.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                      No se encontraron usuarios
                    </td>
                  </tr>
                ) : (
                  filteredUsuarios.map((usuario) => (
                    <tr key={usuario.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <div className="flex items-center">
                          <div className="flex-shrink-0 h-10 w-10">
                            <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                              <span className="text-blue-600 font-semibold text-sm">
                                {usuario.nombre[0]}{usuario.apellido[0]}
                              </span>
                            </div>
                          </div>
                          <div className="ml-4">
                            <div className="text-sm font-medium text-gray-900">
                              {usuario.nombre} {usuario.apellido}
                            </div>
                            <div className="text-sm text-gray-500">
                              {usuario.email}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm">
                          {getRolLabel(usuario.rol)}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          usuario.is_active 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {usuario.is_active ? (
                            <>
                              <UserCheck className="h-3 w-3 mr-1" />
                              Activo
                            </>
                          ) : (
                            <>
                              <UserX className="h-3 w-3 mr-1" />
                              Inactivo
                            </>
                          )}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {usuario.last_login 
                          ? new Date(usuario.last_login).toLocaleDateString('es-ES', {
                              day: '2-digit',
                              month: '2-digit',
                              year: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit'
                            })
                          : 'Nunca'
                        }
                      </td>
                      <td className="px-6 py-4 text-right text-sm font-medium">
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => handleView(usuario)}
                            className="text-blue-600 hover:text-blue-900"
                            title="Ver detalles"
                          >
                            <Eye className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => handleEdit(usuario)}
                            className="text-yellow-600 hover:text-yellow-900"
                            title="Editar"
                          >
                            <Edit2 className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(usuario)}
                            className="text-red-600 hover:text-red-900"
                            title="Eliminar"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Modal Crear/Editar Usuario */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                  {editingUser ? (
                    <>
                      <Edit2 className="h-5 w-5 text-blue-600" />
                      Editar Usuario
                    </>
                  ) : (
                    <>
                      <Plus className="h-5 w-5 text-blue-600" />
                      Nuevo Usuario
                    </>
                  )}
                </h3>
                <button
                  onClick={handleCloseModal}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="h-6 w-6" />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Email */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Email *
                  </label>
                  <Input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    required
                    placeholder="usuario@ejemplo.com"
                  />
                </div>

                {/* Nombre y Apellido */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Nombre *
                    </label>
                    <Input
                      value={formData.nombre}
                      onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                      required
                      placeholder="Nombre"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Apellido *
                    </label>
                    <Input
                      value={formData.apellido}
                      onChange={(e) => setFormData({ ...formData, apellido: e.target.value })}
                      required
                      placeholder="Apellido"
                    />
                  </div>
                </div>

                {/* Rol */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Rol *
                  </label>
                  <select
                    value={formData.rol}
                    onChange={(e) => setFormData({ ...formData, rol: e.target.value as any })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  >
                    {roles.map((rol) => (
                      <option key={rol.value} value={rol.value}>
                        {rol.label} - {rol.description}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Contraseña */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Contraseña {editingUser ? '(dejar en blanco para no cambiar)' : '*'}
                  </label>
                  <Input
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    required={!editingUser}
                    placeholder={editingUser ? 'Nueva contraseña (opcional)' : 'Mínimo 8 caracteres'}
                    minLength={8}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Mínimo 8 caracteres, incluye mayúsculas, minúsculas y números
                  </p>
                </div>

                {/* Estado */}
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-gray-700">
                    Estado del Usuario
                  </label>
                  <div className="flex items-center">
                    <span className={`text-sm mr-3 ${!formData.is_active ? 'text-gray-900' : 'text-gray-500'}`}>
                      OFF
                    </span>
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, is_active: !formData.is_active })}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                        formData.is_active ? 'bg-blue-600' : 'bg-gray-200'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          formData.is_active ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                    <span className={`text-sm ml-3 ${formData.is_active ? 'text-gray-900' : 'text-gray-500'}`}>
                      ON
                    </span>
                  </div>
                </div>

                {/* Botones */}
                <div className="flex justify-end gap-3 pt-4">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleCloseModal}
                  >
                    <X className="h-4 w-4 mr-2" />
                    Cancelar
                  </Button>
                  <Button
                    type="submit"
                    className="bg-blue-600 hover:bg-blue-700 text-white"
                  >
                    <Save className="h-4 w-4 mr-2" />
                    {editingUser ? 'Actualizar' : 'Crear'} Usuario
                  </Button>
                </div>
              </form>
            </div>
          </Card>
        </div>
      )}

      {/* Modal Ver Detalles */}
      {showViewModal && viewingUser && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-2xl">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                  <Eye className="h-5 w-5 text-blue-600" />
                  Detalles del Usuario
                </h3>
                <button
                  onClick={() => setShowViewModal(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="h-6 w-6" />
                </button>
              </div>

              <div className="space-y-4">
                <div className="flex items-center gap-4 pb-4 border-b">
                  <div className="h-16 w-16 rounded-full bg-blue-100 flex items-center justify-center">
                    <span className="text-blue-600 font-bold text-xl">
                      {viewingUser.nombre[0]}{viewingUser.apellido[0]}
                    </span>
                  </div>
                  <div>
                    <h4 className="text-lg font-semibold text-gray-900">
                      {viewingUser.nombre} {viewingUser.apellido}
                    </h4>
                    <p className="text-sm text-gray-600">{viewingUser.email}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm font-medium text-gray-500">Rol</p>
                    <p className="text-sm text-gray-900 mt-1">
                      {getRolLabel(viewingUser.rol)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">Estado</p>
                    <p className="text-sm text-gray-900 mt-1">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        viewingUser.is_active 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {viewingUser.is_active ? 'Activo' : 'Inactivo'}
                      </span>
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">Fecha de creación</p>
                    <p className="text-sm text-gray-900 mt-1">
                      {new Date(viewingUser.created_at).toLocaleDateString('es-ES', {
                        day: '2-digit',
                        month: 'long',
                        year: 'numeric'
                      })}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">Último acceso</p>
                    <p className="text-sm text-gray-900 mt-1">
                      {viewingUser.last_login 
                        ? new Date(viewingUser.last_login).toLocaleDateString('es-ES', {
                            day: '2-digit',
                            month: 'long',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })
                        : 'Nunca'
                      }
                    </p>
                  </div>
                </div>

                {(viewingUser.rol === 'ADMINISTRADOR_GENERAL' || viewingUser.rol === 'GERENTE') && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-4">
                    <div className="flex items-start gap-2">
                      <Shield className="h-5 w-5 text-blue-600 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-blue-900">Permisos Completos</p>
                        <p className="text-xs text-blue-700 mt-1">
                          Este usuario tiene acceso completo a todas las funcionalidades del sistema, incluyendo editar usuarios y herramientas de auditoría
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {viewingUser.rol === 'COBRANZAS' && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mt-4">
                    <div className="flex items-start gap-2">
                      <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-yellow-900">Permisos Limitados</p>
                        <p className="text-xs text-yellow-700 mt-1">
                          Este usuario NO puede editar usuarios ni acceder a herramientas de auditoría. Todas las demás funcionalidades están disponibles.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-3 mt-6 pt-4 border-t">
                <Button
                  variant="outline"
                  onClick={() => setShowViewModal(false)}
                >
                  Cerrar
                </Button>
                <Button
                  onClick={() => {
                    setShowViewModal(false)
                    handleEdit(viewingUser)
                  }}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                  <Edit2 className="h-4 w-4 mr-2" />
                  Editar
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}

