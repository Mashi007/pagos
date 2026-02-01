import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Database, Eye, Download, RefreshCw, Search, Filter } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table'
import { Badge } from '../components/ui/badge'
import { AlertWithIcon } from '../components/ui/alert'
import { LoadingSpinner } from '../components/ui/loading-spinner'

interface DatabaseStats {
  totalClientes: number
  totalPrestamos: number
  totalPagos: number
  carteraActiva: number
  carteraMora: number
}

interface ClienteData {
  id: string
  cedula: string
  nombre: string
  apellido: string
  telefono: string
  email: string
  monto_prestamo: number
  estado: string
  created_at: string
}

export function VisualizacionBD() {
  const [stats, setStats] = useState<DatabaseStats | null>(null)
  const [clientes, setClientes] = useState<ClienteData[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterEstado, setFilterEstado] = useState('')

  useEffect(() => {
    cargarDatos()
  }, [])

  const cargarDatos = async () => {
    setIsLoading(true)
    try {
      // Simular carga de estadÃ­sticas
      setStats({
        totalClientes: 150,
        totalPrestamos: 120,
        totalPagos: 450,
        carteraActiva: 2500000,
        carteraMora: 400000
      })

      // Simular carga de clientes
      const clientesSimulados: ClienteData[] = [
        {
          id: '1',
          cedula: '12345678',
          nombre: 'Juan',
          apellido: 'PÃ©rez',
          telefono: '3001234567',
          email: 'juan@email.com',
          monto_prestamo: 500000,
          estado: 'ACTIVO',
          created_at: '2024-01-15'
        },
        {
          id: '2',
          cedula: '87654321',
          nombre: 'MarÃ­a',
          apellido: 'GarcÃ­a',
          telefono: '3007654321',
          email: 'maria@email.com',
          monto_prestamo: 750000,
          estado: 'MORA',
          created_at: '2024-01-20'
        },
        {
          id: '3',
          cedula: '11223344',
          nombre: 'Carlos',
          apellido: 'LÃ³pez',
          telefono: '3009988776',
          email: 'carlos@email.com',
          monto_prestamo: 300000,
          estado: 'PAGADO',
          created_at: '2024-01-25'
        }
      ]

      setClientes(clientesSimulados)
    } catch (error) {
      console.error('Error al cargar datos:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const clientesFiltrados = clientes.filter(cliente => {
    const matchesSearch =
      cliente.cedula.toLowerCase().includes(searchTerm.toLowerCase()) ||
      cliente.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
      cliente.apellido.toLowerCase().includes(searchTerm.toLowerCase()) ||
      cliente.email.toLowerCase().includes(searchTerm.toLowerCase())

    const matchesEstado = !filterEstado || cliente.estado === filterEstado

    return matchesSearch && matchesEstado
  })

  const exportarDatos = () => {
    const csvContent = [
      ['CÃ©dula', 'Nombre', 'Apellido', 'TelÃ©fono', 'Email', 'Monto PrÃ©stamo', 'Estado', 'Fecha Registro'],
      ...clientesFiltrados.map(cliente => [
        cliente.cedula,
        cliente.nombre,
        cliente.apellido,
        cliente.telefono,
        cliente.email,
        cliente.monto_prestamo.toString(),
        cliente.estado,
        cliente.created_at
      ])
    ].map(row => row.join(',')).join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `base_datos_rapicredit_${new Date().toISOString().split('T')[0]}.csv`
    link.click()
  }

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <LoadingSpinner size="lg" text="Cargando base de datos..." />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center space-x-2">
            <Database className="h-8 w-8 text-blue-600" />
            <span>VisualizaciÃ³n de Base de Datos</span>
          </h1>
          <p className="text-gray-600 mt-2">
            Explora y gestiona todos los datos de tu sistema RAPICREDIT
          </p>
        </div>
        <div className="flex space-x-2">
          <Button onClick={cargarDatos} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Actualizar
          </Button>
          <Button onClick={exportarDatos} className="bg-green-600 hover:bg-green-700">
            <Download className="h-4 w-4 mr-2" />
            Exportar CSV
          </Button>
        </div>
      </motion.div>

      {/* EstadÃ­sticas */}
      {stats && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4"
        >
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Database className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Total Clientes</p>
                  <p className="text-2xl font-bold text-blue-600">{stats.totalClientes}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <div className="p-2 bg-green-100 rounded-lg">
                  <Eye className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">PrÃ©stamos</p>
                  <p className="text-2xl font-bold text-green-600">{stats.totalPrestamos}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <RefreshCw className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Pagos</p>
                  <p className="text-2xl font-bold text-purple-600">{stats.totalPagos}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <div className="p-2 bg-yellow-100 rounded-lg">
                  <Eye className="h-5 w-5 text-yellow-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Cartera Activa</p>
                  <p className="text-lg font-bold text-yellow-600">
                    ${stats.carteraActiva.toLocaleString()}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <div className="p-2 bg-red-100 rounded-lg">
                  <Eye className="h-5 w-5 text-red-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Cartera Mora</p>
                  <p className="text-lg font-bold text-red-600">
                    ${stats.carteraMora.toLocaleString()}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Filtros */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Filter className="h-5 w-5" />
              <span>Filtros y BÃºsqueda</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">
                  Buscar por cÃ©dula, nombre, apellido o email:
                </label>
                <Input
                  placeholder="Buscar..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  leftIcon={<Search className="h-4 w-4 text-gray-400" />}
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">
                  Filtrar por estado:
                </label>
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  value={filterEstado}
                  onChange={(e) => setFilterEstado(e.target.value)}
                >
                  <option value="">Todos los estados</option>
                  <option value="ACTIVO">Activo</option>
                  <option value="MORA">Mora</option>
                  <option value="PAGADO">Pagado</option>
                  <option value="PENDIENTE">Pendiente</option>
                </select>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Tabla de datos */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center space-x-2">
                <Eye className="h-5 w-5" />
                <span>Datos de Clientes ({clientesFiltrados.length} registros)</span>
              </span>
              <Badge variant="outline">
                {clientesFiltrados.length} de {clientes.length}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>CÃ©dula</TableHead>
                    <TableHead>Nombre Completo</TableHead>
                    <TableHead>TelÃ©fono</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Monto PrÃ©stamo</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Fecha Registro</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {clientesFiltrados.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8 text-gray-500">
                        No se encontraron registros con los filtros aplicados.
                      </TableCell>
                    </TableRow>
                  ) : (
                    clientesFiltrados.map((cliente) => (
                      <TableRow key={cliente.id}>
                        <TableCell className="font-medium">{cliente.cedula}</TableCell>
                        <TableCell>{cliente.nombre} {cliente.apellido}</TableCell>
                        <TableCell>{cliente.telefono}</TableCell>
                        <TableCell>{cliente.email}</TableCell>
                        <TableCell>${cliente.monto_prestamo.toLocaleString()}</TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              cliente.estado === 'ACTIVO' ? 'success' :
                              cliente.estado === 'MORA' ? 'destructive' :
                              cliente.estado === 'PAGADO' ? 'secondary' : 'outline'
                            }
                          >
                            {cliente.estado}
                          </Badge>
                        </TableCell>
                        <TableCell>{cliente.created_at}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* InformaciÃ³n adicional */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
      >
        <AlertWithIcon
          variant="info"
          title="InformaciÃ³n de la Base de Datos"
          description={`â€¢ Total de registros: ${clientes.length} clientes\nâ€¢ Ãšltima actualizaciÃ³n: ${new Date().toLocaleString()}\nâ€¢ Formato de exportaciÃ³n: CSV compatible con Excel\nâ€¢ Filtros aplicados: ${searchTerm ? `BÃºsqueda: "${searchTerm}"` : 'Sin bÃºsqueda'} ${filterEstado ? `| Estado: ${filterEstado}` : ''}`}
        />
      </motion.div>
    </div>
  )
}
