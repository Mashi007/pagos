import { useState } from 'react'
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
  Award
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

export function Asesores() {
  const [searchTerm, setSearchTerm] = useState('')

  // Mock data - reemplazar con useQuery
  const analistaes = [
    {
      id: 1,
      nombre: 'Roberto',
      apellido: 'Martínez',
      email: 'roberto.martinez@rapicredit.com',
      telefono: '+58 414-555-0404',
      especialidad: 'Vehículos Nuevos',
      comision_porcentaje: 2.5,
      activo: true,
      clientes_asignados: 15,
      ventas_mes: 5
    },
    {
      id: 2,
      nombre: 'Sandra',
      apellido: 'López',
      email: 'sandra.lopez@rapicredit.com',
      telefono: '+58 424-555-0505',
      especialidad: 'Vehículos Usados',
      comision_porcentaje: 3.0,
      activo: true,
      clientes_asignados: 12,
      ventas_mes: 3
    }
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Asesores Comerciales</h1>
          <p className="text-gray-500 mt-1">
            Gestión de analistaes y equipo de ventas
          </p>
        </div>
        <Button>
          <Plus className="w-4 h-4 mr-2" />
          Nuevo Asesor
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Asesores</p>
                <p className="text-2xl font-bold">{analistaes.length}</p>
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
                  {analistaes.filter(a => a.activo).length}
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
                <p className="text-sm text-gray-500">Clientes Asignados</p>
                <p className="text-2xl font-bold">
                  {analistaes.reduce((sum, a) => sum + a.clientes_asignados, 0)}
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
                <p className="text-sm text-gray-500">Ventas Este Mes</p>
                <p className="text-2xl font-bold text-purple-600">
                  {analistaes.reduce((sum, a) => sum + a.ventas_mes, 0)}
                </p>
              </div>
              <Award className="w-8 h-8 text-purple-600" />
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
                <TableHead>Asesor</TableHead>
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
              {analistaes.map((analista) => (
                <TableRow key={analista.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">{analista.nombre} {analista.apellido}</p>
                      <p className="text-xs text-gray-500">ID: {analista.id}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="space-y-1">
                      <div className="flex items-center text-sm">
                        <Mail className="w-3 h-3 mr-1 text-gray-400" />
                        {analista.email}
                      </div>
                      <div className="flex items-center text-sm">
                        <Phone className="w-3 h-3 mr-1 text-gray-400" />
                        {analista.telefono}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{analista.especialidad}</Badge>
                  </TableCell>
                  <TableCell>{analista.comision_porcentaje}%</TableCell>
                  <TableCell>{analista.clientes_asignados}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className="bg-purple-50">
                      {analista.ventas_mes}
                    </Badge>
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
                      <Button variant="ghost" size="sm">
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button variant="ghost" size="sm">
                        {analista.activo ? (
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

