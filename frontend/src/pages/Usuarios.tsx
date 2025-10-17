import { useState, useEffect } from 'react'
import { Users, Plus, Search, Edit, Trash2, Shield, Mail, UserCheck, UserX, Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { usuarioService, Usuario } from '@/services/usuarioService'
import { toast } from 'sonner'

export function Usuarios() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingUsuario, setEditingUsuario] = useState<Usuario | null>(null)

  // Cargar usuarios al montar el componente
  useEffect(() => {
    cargarUsuarios()
  }, [])

  const cargarUsuarios = async () => {
    try {
      setLoading(true)
      setError(null)
      console.log('📡 Llamando a API: /api/v1/users')
      const response = await usuarioService.listarUsuarios({ limit: 100 })
      console.log('✅ Respuesta API:', response)
      setUsuarios(response.items)
    } catch (err) {
      console.error('❌ Error API:', err)
      setError('Error al cargar usuarios')
      toast.error('Error al cargar usuarios')
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

  // Filtrar usuarios por término de búsqueda
  const usuariosFiltrados = usuarios.filter(usuario =>
    usuario.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
    usuario.apellido.toLowerCase().includes(searchTerm.toLowerCase()) ||
    usuario.email.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const getRoleBadgeColor = (rol: string) => {
    const colors: any = {
      'USER': 'bg-blue-600',
      'ASESOR_COMERCIAL': 'bg-blue-600',
      'COBRADOR': 'bg-green-600',
      'CONTADOR': 'bg-yellow-600',
      'AUDITOR': 'bg-gray-600'
    }
    return colors[rol] || 'bg-gray-600'
  }

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
        <Button onClick={() => setShowCreateForm(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Nuevo Usuario
        </Button>
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
                  {usuarios.length > 0 ? `${((usuarios.filter(u => u.is_active).length / usuarios.length) * 100).toFixed(1)}% activos` : 'Sin datos'}
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
                  Pueden acceder al sistema
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
                  Pueden crear usuarios
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
                  Usuarios agregados
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
    </div>
  )
}

