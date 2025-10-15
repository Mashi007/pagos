import { useState } from 'react'
import { Car, Plus, Search, Edit, Trash2, CheckCircle, XCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

export function ModelosVehiculos() {
  const [searchTerm, setSearchTerm] = useState('')
  const [categoriaFilter, setCategoriaFilter] = useState('TODOS')

  // Mock data - reemplazar con useQuery
  const modelos = [
    { id: 1, marca: 'Toyota', modelo: 'Corolla', nombre_completo: 'Toyota Corolla', categoria: 'SEDAN', activo: true },
    { id: 2, marca: 'Nissan', modelo: 'Versa', nombre_completo: 'Nissan Versa', categoria: 'SEDAN', activo: true },
    { id: 3, marca: 'Hyundai', modelo: 'Tucson', nombre_completo: 'Hyundai Tucson', categoria: 'SUV', activo: true },
    { id: 4, marca: 'Ford', modelo: 'F-150', nombre_completo: 'Ford F-150', categoria: 'PICKUP', activo: true },
    { id: 5, marca: 'Chevrolet', modelo: 'Spark', nombre_completo: 'Chevrolet Spark', categoria: 'COMPACTO', activo: false }
  ]

  const categorias = ['TODOS', 'SEDAN', 'SUV', 'PICKUP', 'COMPACTO', 'DEPORTIVO']

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Modelos de Vehículos</h1>
          <p className="text-gray-500 mt-1">
            Catálogo de modelos disponibles para financiamiento
          </p>
        </div>
        <Button>
          <Plus className="w-4 h-4 mr-2" />
          Agregar Modelo
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Modelos</p>
                <p className="text-2xl font-bold">{modelos.length}</p>
              </div>
              <Car className="w-8 h-8 text-primary" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Activos</p>
                <p className="text-2xl font-bold text-green-600">
                  {modelos.filter(m => m.activo).length}
                </p>
              </div>
              <CheckCircle className="w-8 h-8 text-green-600" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Inactivos</p>
                <p className="text-2xl font-bold text-red-600">
                  {modelos.filter(m => !m.activo).length}
                </p>
              </div>
              <XCircle className="w-8 h-8 text-red-600" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Marcas</p>
                <p className="text-2xl font-bold text-blue-600">
                  {new Set(modelos.map(m => m.marca)).size}
                </p>
              </div>
              <Car className="w-8 h-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filtros */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Buscar modelo o marca..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <select
              className="px-4 py-2 border rounded-lg"
              value={categoriaFilter}
              onChange={(e) => setCategoriaFilter(e.target.value)}
            >
              {categorias.map((cat) => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Tabla */}
      <Card>
        <CardContent className="pt-6">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Modelo</TableHead>
                <TableHead>Marca</TableHead>
                <TableHead>Categoría</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {modelos.map((modelo) => (
                <TableRow key={modelo.id}>
                  <TableCell>
                    <div className="flex items-center space-x-3">
                      <Car className="w-5 h-5 text-gray-400" />
                      <div>
                        <p className="font-medium">{modelo.nombre_completo}</p>
                        <p className="text-xs text-gray-500">ID: {modelo.id}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{modelo.marca}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary">{modelo.categoria}</Badge>
                  </TableCell>
                  <TableCell>
                    {modelo.activo ? (
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
                        {modelo.activo ? (
                          <XCircle className="w-4 h-4 text-red-600" />
                        ) : (
                          <CheckCircle className="w-4 h-4 text-green-600" />
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

