// frontend/src/components/configuracion/UsuariosConfig.tsx
import { useState, useEffect } from 'react'
import { Button } from '../../components/ui/button'
import { Card } from '../../components/ui/card'
import { Input } from '../../components/ui/input'
import { PasswordField } from '../../components/ui/PasswordField'
import { usePassword } from '../../hooks/usePassword'
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
import { userService, type UserCreate, type UserUpdate } from '../../services/userService'
import { User } from '../../types'
import { toast } from 'react-hot-toast'
import { apiClient } from '../../services/api'

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

  // Función para validar email con el sistema
  const validateEmailWithSystem = async (email: string) => {
    try {
      const { data: result } = await apiClient.post<{
        validacion?: { valido: boolean; valor_formateado?: string; error?: string; sugerencia?: string }
      }>('/api/v1/validadores/validar-campo', {
        campo: 'email',
        valor: email,
        pais: 'VENEZUELA'
      })

      if (result) {
        if (result.validacion && result.validacion.valido) {
          return {
            isValid: true,
            formattedValue: result.validacion.valor_formateado
          }
        }
        // Mostrar error y sugerencia si está disponible
        const errorMsg = result.validacion?.error || 'Formato de email inválido'
        const sugerencia = result.validacion?.sugerencia || ''
        const mensajeCompleto = sugerencia ? `${errorMsg}. ${sugerencia}` : errorMsg
        return {
          isValid: false,
          message: mensajeCompleto
        }
      }
    } catch {
      // Endpoint no disponible o error de red: usar validación local
    }

    // Fallback: validación local
    const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
    if (!emailPattern.test(email.toLowerCase())) {
      return { isValid: false, message: 'Formato: usuario@dominio.com' }
    }

    return { isValid: true, formattedValue: email.toLowerCase() }
  }

  const [formData, setFormData] = useState<UserCreate>({
    email: '',
    nombre: '',
    apellido: '',
    is_admin: false,  // Cambio clave: rol â†’ is_admin
    password: '',
    cargo: 'Usuario', // Valor por defecto para evitar error de NOT NULL
    is_active: true
  })

  // Hook para validar contraseña
  const { validatePassword } = usePassword()

  useEffect(() => {
    loadUsuarios()
  }, [filterActive])

  const loadUsuarios = async () => {
    try {
      setLoading(true)
      const data = await userService.listarUsuarios(1, 100, filterActive)
      setUsuarios(data.items)
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

  // Validación del formulario
  const isFormValid = () => {
    if (!formData.email || !formData.nombre || !formData.apellido) {
      return false
    }

    // Si estamos creando un nuevo usuario, la contraseña es obligatoria
    if (!editingUser && !formData.password) {
      return false
    }

    // Si hay una contraseña (ya sea en creación o actualización), debe cumplir todos los requisitos
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

    if (!isFormValid()) {
      toast.error('Por favor completa todos los campos requeridos')
      return
    }

    try {
      // Validar email con el validador del sistema
      const emailValidation = await validateEmailWithSystem(formData.email)
      if (!emailValidation.isValid) {
        toast.error(emailValidation.message || 'Email inválido')
        return
      }

      if (editingUser) {
        // Actualizar
        const updateData: UserUpdate = {
          email: emailValidation.formattedValue || formData.email.toLowerCase(),
          nombre: formData.nombre,
          apellido: formData.apellido,
          cargo: formData.cargo, // Incluir cargo para preservarlo
          is_admin: formData.is_admin,  // Cambio clave: rol â†’ is_admin
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
        const createData: UserCreate = {
          email: emailValidation.formattedValue || formData.email.toLowerCase(),
          nombre: formData.nombre,
          apellido: formData.apellido,
          is_admin: formData.is_admin,
          password: formData.password,
          cargo: formData.cargo,
          is_active: formData.is_active
        }
        await userService.crearUsuario(createData)
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
      email: usuario.email.toLowerCase(), // Normalizar a minúsculas
      nombre: usuario.nombre,
      apellido: usuario.apellido,
      cargo: usuario.cargo || 'Usuario', // Preservar cargo existente
      is_admin: usuario.is_admin,  // Cambio clave: rol â†’ is_admin
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
    if (!confirm(`¿Estás seguro de eliminar el usuario ${usuario.nombre} ${usuario.apellido} (${usuario.email})?`)) {
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
      is_admin: false,  // Cambio clave: rol â†’ is_admin
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
    (user.email && user.email.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (user.nombre && user.nombre.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (user.apellido && user.apellido.toLowerCase().includes(searchTerm.toLowerCase()))
  )

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
            Administra usuarios del sistema - Todos tienen acceso completo
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
              placeholder="Buscar por nombre o email..."
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
                    Estado
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Ãšltimo acceso
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

              <form onSubmit={handleSubmit} className="space-y-4" autoComplete="off">
                {/* Email */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Email *
                  </label>
                  <Input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value.toLowerCase() })}
                    required
                    placeholder="usuario@ejemplo.com"
                    autoComplete="off"
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
                      autoComplete="off"
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
                      autoComplete="off"
                    />
                  </div>
                </div>

                {/* Cargo */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Cargo
                  </label>
                  <Input
                    value={formData.cargo || ''}
                    onChange={(e) => setFormData({ ...formData, cargo: e.target.value })}
                    placeholder="Ej: Gerente, Analista, etc."
                    autoComplete="off"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Cargo del usuario en la empresa (opcional)
                  </p>
                </div>

                {/* Rol */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Tipo de Usuario
                  </label>
                  <div className="flex items-center space-x-4">
                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="is_admin"
                        checked={!formData.is_admin}
                        onChange={() => setFormData({ ...formData, is_admin: false })}
                        className="mr-2"
                      />
                      <span className="text-sm text-gray-700">Usuario Normal</span>
                    </label>
                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="is_admin"
                        checked={formData.is_admin}
                        onChange={() => setFormData({ ...formData, is_admin: true })}
                        className="mr-2"
                      />
                      <span className="text-sm text-gray-700">Administrador</span>
                    </label>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Los administradores tienen acceso completo al sistema
                  </p>
                </div>

                {/* Contraseña */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Contraseña {editingUser ? '(dejar en blanco para no cambiar)' : '*'}
                  </label>
                  <PasswordField
                    value={formData.password}
                    onChange={(password) => setFormData({ ...formData, password })}
                    placeholder={editingUser ? 'Nueva contraseña (opcional)' : 'Mínimo 8 caracteres'}
                    required={!editingUser}
                    showGenerateButton={true}  // âœ… SIEMPRE mostrar botón de generar
                    showCopyButton={true}      // âœ… SIEMPRE mostrar botón de copiar
                  />
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
                    disabled={!isFormValid()}
                    className="bg-blue-600 hover:bg-blue-700 text-white disabled:bg-gray-400 disabled:cursor-not-allowed"
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
                    <p className="text-sm font-medium text-gray-500">Ãšltimo acceso</p>
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

                <div className="bg-green-50 border border-green-200 rounded-lg p-4 mt-4">
                  <div className="flex items-start gap-2">
                    <Shield className="h-5 w-5 text-green-600 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-green-900">Acceso Completo</p>
                      <p className="text-xs text-green-700 mt-1">
                        Todos los usuarios tienen acceso completo a todas las funcionalidades del sistema
                      </p>
                    </div>
                  </div>
                </div>
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

