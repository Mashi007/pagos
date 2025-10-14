import { useState } from 'react'
import { motion } from 'framer-motion'
import { 
  CreditCard, 
  Search, 
  Filter, 
  Plus, 
  Download,
  Calendar,
  DollarSign,
  CheckCircle,
  AlertCircle,
  Clock
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'

// Mock data para pagos
const mockPagos = [
  {
    id: 1,
    cliente: 'Juan Carlos Pérez González',
    cedula: '12345678',
    monto: 850.00,
    fecha: '2024-01-15',
    metodo: 'Transferencia',
    estado: 'confirmado',
    referencia: 'TXN-001234',
    prestamo_id: 1
  },
  {
    id: 2,
    cliente: 'María Elena Rodríguez López',
    cedula: '87654321',
    monto: 1200.00,
    fecha: '2024-01-15',
    metodo: 'Efectivo',
    estado: 'confirmado',
    referencia: 'EFE-001235',
    prestamo_id: 2
  },
  {
    id: 3,
    cliente: 'Carlos Alberto Martínez Silva',
    cedula: '11223344',
    monto: 950.00,
    fecha: '2024-01-14',
    metodo: 'Cheque',
    estado: 'pendiente',
    referencia: 'CHK-001236',
    prestamo_id: 3
  }
]

export function Pagos() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterEstado, setFilterEstado] = useState('')

  const getEstadoBadge = (estado: string) => {
    switch (estado) {
      case 'confirmado':
        return <Badge className="bg-green-100 text-green-800"><CheckCircle className="w-3 h-3 mr-1" />Confirmado</Badge>
      case 'pendiente':
        return <Badge className="bg-yellow-100 text-yellow-800"><Clock className="w-3 h-3 mr-1" />Pendiente</Badge>
      case 'rechazado':
        return <Badge className="bg-red-100 text-red-800"><AlertCircle className="w-3 h-3 mr-1" />Rechazado</Badge>
      default:
        return <Badge variant="secondary">{estado}</Badge>
    }
  }

  const filteredPagos = mockPagos.filter(pago => {
    const matchesSearch = pago.cliente.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         pago.cedula.includes(searchTerm) ||
                         pago.referencia.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesEstado = !filterEstado || pago.estado === filterEstado
    return matchesSearch && matchesEstado
  })

  const totalConfirmado = mockPagos
    .filter(p => p.estado === 'confirmado')
    .reduce((sum, p) => sum + p.monto, 0)

  const totalPendiente = mockPagos
    .filter(p => p.estado === 'pendiente')
    .reduce((sum, p) => sum + p.monto, 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Gestión de Pagos</h1>
            <p className="text-gray-600 mt-1">Administra y monitorea todos los pagos del sistema</p>
          </div>
          <Button className="bg-blue-600 hover:bg-blue-700">
            <Plus className="w-4 h-4 mr-2" />
            Nuevo Pago
          </Button>
        </div>
      </motion.div>

      {/* Stats Cards */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.5 }}
        className="grid grid-cols-1 md:grid-cols-3 gap-6"
      >
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Confirmado</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              ${totalConfirmado.toLocaleString('es-ES', { minimumFractionDigits: 2 })}
            </div>
            <p className="text-xs text-gray-600">Pagos confirmados hoy</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pendientes</CardTitle>
            <Clock className="h-4 w-4 text-yellow-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">
              ${totalPendiente.toLocaleString('es-ES', { minimumFractionDigits: 2 })}
            </div>
            <p className="text-xs text-gray-600">Esperando confirmación</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Pagos</CardTitle>
            <DollarSign className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">
              {mockPagos.length}
            </div>
            <p className="text-xs text-gray-600">Registros en el sistema</p>
          </CardContent>
        </Card>
      </motion.div>

      {/* Filters */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.5 }}
      >
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Filter className="w-5 h-5 mr-2" />
              Filtros y Búsqueda
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Buscar por cliente, cédula o referencia..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
              <select
                value={filterEstado}
                onChange={(e) => setFilterEstado(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Todos los estados</option>
                <option value="confirmado">Confirmado</option>
                <option value="pendiente">Pendiente</option>
                <option value="rechazado">Rechazado</option>
              </select>
              <Button variant="outline" className="flex items-center">
                <Download className="w-4 h-4 mr-2" />
                Exportar
              </Button>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Pagos List */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.5 }}
      >
        <Card>
          <CardHeader>
            <CardTitle>Registro de Pagos</CardTitle>
            <CardDescription>
              Lista de todos los pagos registrados en el sistema
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {filteredPagos.map((pago) => (
                <div key={pago.id} className="border rounded-lg p-4 hover:bg-gray-50 transition-colors">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3">
                        <CreditCard className="w-5 h-5 text-blue-600" />
                        <div>
                          <h3 className="font-semibold text-gray-900">{pago.cliente}</h3>
                          <p className="text-sm text-gray-600">Cédula: {pago.cedula}</p>
                        </div>
                      </div>
                      <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <span className="text-gray-500">Monto:</span>
                          <p className="font-medium">${pago.monto.toLocaleString('es-ES', { minimumFractionDigits: 2 })}</p>
                        </div>
                        <div>
                          <span className="text-gray-500">Método:</span>
                          <p className="font-medium">{pago.metodo}</p>
                        </div>
                        <div>
                          <span className="text-gray-500">Fecha:</span>
                          <p className="font-medium">{new Date(pago.fecha).toLocaleDateString('es-ES')}</p>
                        </div>
                        <div>
                          <span className="text-gray-500">Referencia:</span>
                          <p className="font-medium">{pago.referencia}</p>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-3">
                      {getEstadoBadge(pago.estado)}
                      <Button variant="outline" size="sm">
                        Ver Detalles
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
              
              {filteredPagos.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <CreditCard className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                  <p>No se encontraron pagos con los filtros aplicados</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}
