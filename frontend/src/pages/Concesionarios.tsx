import { useState } from 'react'
import { Building, Plus, Search, Edit, Trash2, MapPin, Phone, Mail, User } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

export function Concesionarios() {
  const [searchTerm, setSearchTerm] = useState('')

  // Mock data - reemplazar con useQuery
  const concesionarios = [
    {
      id: 1,
      nombre: 'AutoCenter Caracas',
      direccion: 'Av. Francisco de Miranda, Caracas',
      telefono: '+58 212-555-0101',
      email: 'caracas@autocenter.com',
      responsable: 'María González',
      activo: true,
      clientes_referidos: 25
    },
    {
      id: 2,
      nombre: 'Motors Valencia',
      direccion: 'Zona Industrial Norte, Valencia',
      telefono: '+58 241-555-0202',
      email: 'valencia@motors.com',
      responsable: 'Carlos Rodríguez',
      activo: true,
      clientes_referidos: 18
    }
  ]

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
        <Button>
          <Plus className="w-4 h-4 mr-2" />
          Nuevo Concesionario
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Concesionarios</p>
                <p className="text-2xl font-bold">{concesionarios.length}</p>
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
              </div>
              <Building className="w-8 h-8 text-green-600" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Clientes Referidos</p>
                <p className="text-2xl font-bold text-blue-600">
                  {concesionarios.reduce((sum, c) => sum + c.clientes_referidos, 0)}
                </p>
              </div>
              <User className="w-8 h-8 text-blue-600" />
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
              {concesionarios.map((concesionario) => (
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
                    <div className="flex items-center text-sm">
                      <MapPin className="w-3 h-3 mr-1 text-gray-400" />
                      {concesionario.direccion}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="space-y-1">
                      <div className="flex items-center text-sm">
                        <Mail className="w-3 h-3 mr-1 text-gray-400" />
                        {concesionario.email}
                      </div>
                      <div className="flex items-center text-sm">
                        <Phone className="w-3 h-3 mr-1 text-gray-400" />
                        {concesionario.telefono}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center text-sm">
                      <User className="w-3 h-3 mr-1 text-gray-400" />
                      {concesionario.responsable}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{concesionario.clientes_referidos}</Badge>
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
                      <Button variant="ghost" size="sm">
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button variant="ghost" size="sm">
                        <Trash2 className="w-4 h-4 text-red-600" />
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

