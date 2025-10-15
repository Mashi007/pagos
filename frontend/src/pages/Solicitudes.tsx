import { useState } from 'react'
import { FileText, Search, CheckCircle, XCircle, Clock, Eye } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

export function Solicitudes() {
  const [searchTerm, setSearchTerm] = useState('')

  // Mock data
  const solicitudes = [
    {
      id: 1,
      cliente: 'Juan Pérez',
      cedula: 'V12345678',
      tipo: 'PRESTAMO',
      monto: 25000,
      estado: 'PENDIENTE',
      fecha: '2025-10-14'
    },
    {
      id: 2,
      cliente: 'María García',
      cedula: 'V23456789',
      tipo: 'AMPLIACION',
      monto: 15000,
      estado: 'APROBADA',
      fecha: '2025-10-13'
    }
  ]

  const getEstadoBadge = (estado: string) => {
    const estados: any = {
      'PENDIENTE': { color: 'bg-yellow-600', icon: Clock },
      'APROBADA': { color: 'bg-green-600', icon: CheckCircle },
      'RECHAZADA': { color: 'bg-red-600', icon: XCircle }
    }
    return estados[estado] || { color: 'bg-gray-600', icon: FileText }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Solicitudes</h1>
          <p className="text-gray-500 mt-1">Gestión de solicitudes de préstamos</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Pendientes</p>
                <p className="text-2xl font-bold text-yellow-600">
                  {solicitudes.filter(s => s.estado === 'PENDIENTE').length}
                </p>
              </div>
              <Clock className="w-8 h-8 text-yellow-600" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Aprobadas</p>
                <p className="text-2xl font-bold text-green-600">
                  {solicitudes.filter(s => s.estado === 'APROBADA').length}
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
                <p className="text-sm text-gray-500">Rechazadas</p>
                <p className="text-2xl font-bold text-red-600">
                  {solicitudes.filter(s => s.estado === 'RECHAZADA').length}
                </p>
              </div>
              <XCircle className="w-8 h-8 text-red-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="relative mb-6">
            <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Buscar solicitud..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Cliente</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead>Monto</TableHead>
                <TableHead>Fecha</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {solicitudes.map((solicitud) => (
                <TableRow key={solicitud.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">{solicitud.cliente}</p>
                      <p className="text-xs text-gray-500">{solicitud.cedula}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{solicitud.tipo}</Badge>
                  </TableCell>
                  <TableCell className="font-medium">
                    ${solicitud.monto.toLocaleString()}
                  </TableCell>
                  <TableCell>{solicitud.fecha}</TableCell>
                  <TableCell>
                    <Badge className={getEstadoBadge(solicitud.estado).color}>
                      {solicitud.estado}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end space-x-2">
                      <Button variant="ghost" size="sm">
                        <Eye className="w-4 h-4" />
                      </Button>
                      {solicitud.estado === 'PENDIENTE' && (
                        <>
                          <Button variant="ghost" size="sm">
                            <CheckCircle className="w-4 h-4 text-green-600" />
                          </Button>
                          <Button variant="ghost" size="sm">
                            <XCircle className="w-4 h-4 text-red-600" />
                          </Button>
                        </>
                      )}
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

