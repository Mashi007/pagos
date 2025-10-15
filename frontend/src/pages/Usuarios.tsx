import { useState } from 'react'
import { Users, Plus, Search, Edit, Trash2, Shield, Mail, UserCheck, UserX } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

export function Usuarios() {
  const [searchTerm, setSearchTerm] = useState('')

  // Mock data - reemplazar con useQuery
  const usuarios = [
    {
      id: 1,
      nombre: 'Admin',
      apellido: 'Sistema',
      email: 'itmaster@rapicreditca.com',
      rol: 'ADMIN',
      activo: true,
      ultimo_acceso: '2025-10-15'
    },
    {
      id: 2,
      nombre: 'Roberto',
      apellido: 'Martínez',
      email: 'roberto.martinez@rapicredit.com',
      rol: 'ASESOR_COMERCIAL',
      activo: true,
      ultimo_acceso: '2025-10-14'
    },
    {
      id: 3,
      nombre: 'María',
      apellido: 'González',
      email: 'maria.gonzalez@rapicredit.com',
      rol: 'GERENTE',
      activo: true,
      ultimo_acceso: '2025-10-15'
    }
  ]

  const roles = ['TODOS', 'ADMIN', 'GERENTE', 'ASESOR_COMERCIAL', 'COBRADOR', 'CONTADOR', 'AUDITOR']

  const getRoleBadgeColor = (rol: string) => {
    const colors: any = {
      'ADMIN': 'bg-red-600',
      'GERENTE': 'bg-purple-600',
      'ASESOR_COMERCIAL': 'bg-blue-600',
      'COBRADOR': 'bg-green-600',
      'CONTADOR': 'bg-yellow-600',
      'AUDITOR': 'bg-gray-600'
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
        <Button>
          <Plus className="w-4 h-4 mr-2" />
          Nuevo Usuario
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Usuarios</p>
                <p className="text-2xl font-bold">{usuarios.length}</p>
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
                  {usuarios.filter(u => u.activo).length}
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
              </div>
              <Shield className="w-8 h-8 text-red-600" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Asesores</p>
                <p className="text-2xl font-bold text-blue-600">
                  {usuarios.filter(u => u.rol === 'ASESOR_COMERCIAL').length}
                </p>
              </div>
              <Users className="w-8 h-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Búsqueda y filtros */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Buscar usuario por nombre o email..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
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
                <TableHead>Último Acceso</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {usuarios.map((usuario) => (
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
                    {usuario.ultimo_acceso}
                  </TableCell>
                  <TableCell>
                    {usuario.activo ? (
                      <Badge className="bg-green-600">Activo</Badge>
                    ) : (
                      <Badge variant="outline">Inactivo</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end space-x-2">
                      <Button variant="ghost" size="sm">
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button variant="ghost" size="sm">
                        {usuario.activo ? (
                          <UserX className="w-4 h-4 text-red-600" />
                        ) : (
                          <UserCheck className="w-4 h-4 text-green-600" />
                        )}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}

