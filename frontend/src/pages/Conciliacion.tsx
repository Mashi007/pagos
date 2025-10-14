import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  RefreshCw,
  Upload,
  Download,
  CheckCircle,
  XCircle,
  AlertTriangle,
  DollarSign,
  Calendar,
  FileText,
  Search,
  Filter,
  ArrowDownToLine,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatCurrency, formatDate } from '@/utils'

// Mock data para conciliación
const mockConciliaciones = [
  {
    id: 'CONC001',
    fecha: '2024-07-20',
    banco: 'Banco de Venezuela',
    archivo: 'extracto_20240720.xlsx',
    totalRegistros: 45,
    coincidencias: 42,
    discrepancias: 3,
    montoTotal: 12500.00,
    estado: 'COMPLETADA',
    procesadoPor: 'admin@financiamiento.com',
  },
  {
    id: 'CONC002',
    fecha: '2024-07-19',
    banco: 'Banesco',
    archivo: 'movimientos_19072024.csv',
    totalRegistros: 28,
    coincidencias: 25,
    discrepancias: 3,
    montoTotal: 8750.00,
    estado: 'PENDIENTE',
    procesadoPor: 'admin@financiamiento.com',
  },
  {
    id: 'CONC003',
    fecha: '2024-07-18',
    banco: 'Mercantil',
    archivo: 'conciliacion_18072024.xlsx',
    totalRegistros: 67,
    coincidencias: 60,
    discrepancias: 7,
    montoTotal: 18900.00,
    estado: 'ERROR',
    procesadoPor: 'admin@financiamiento.com',
  },
]

const mockDiscrepancias = [
  {
    id: 'DISC001',
    conciliacionId: 'CONC001',
    tipo: 'MONTO_DIFERENTE',
    descripcion: 'Pago de $450.00 vs $500.00 registrado',
    montoSistema: 500.00,
    montoBanco: 450.00,
    diferencia: 50.00,
    referencia: 'TRF789012',
    fecha: '2024-07-20',
    estado: 'PENDIENTE',
  },
  {
    id: 'DISC002',
    conciliacionId: 'CONC001',
    tipo: 'NO_ENCONTRADO',
    descripcion: 'Pago no encontrado en sistema',
    montoSistema: 0.00,
    montoBanco: 850.00,
    diferencia: -850.00,
    referencia: 'EFE345678',
    fecha: '2024-07-20',
    estado: 'PENDIENTE',
  },
  {
    id: 'DISC003',
    conciliacionId: 'CONC002',
    tipo: 'FECHA_DIFERENTE',
    descripcion: 'Fecha de pago diferente',
    montoSistema: 1200.00,
    montoBanco: 1200.00,
    diferencia: 0.00,
    referencia: 'CHQ901234',
    fecha: '2024-07-19',
    estado: 'RESUELTA',
  },
]

export function Conciliacion() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterStatus, setFilterStatus] = useState('Todos')
  const [selectedConciliacion, setSelectedConciliacion] = useState<string | null>(null)

  const filteredConciliaciones = mockConciliaciones.filter((conc) => {
    const matchesSearch =
      conc.banco.toLowerCase().includes(searchTerm.toLowerCase()) ||
      conc.archivo.toLowerCase().includes(searchTerm.toLowerCase()) ||
      conc.id.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = filterStatus === 'Todos' || conc.estado === filterStatus
    return matchesSearch && matchesStatus
  })

  const totalConciliaciones = mockConciliaciones.length
  const conciliacionesCompletadas = mockConciliaciones.filter((c) => c.estado === 'COMPLETADA').length
  const conciliacionesPendientes = mockConciliaciones.filter((c) => c.estado === 'PENDIENTE').length
  const totalDiscrepancias = mockDiscrepancias.filter((d) => d.estado === 'PENDIENTE').length

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <h1 className="text-3xl font-bold text-gray-900">Conciliación Bancaria</h1>
      <p className="text-gray-600">Gestiona la conciliación entre los pagos del sistema y los extractos bancarios.</p>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Conciliaciones</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalConciliaciones}</div>
            <p className="text-xs text-muted-foreground">Procesos realizados</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completadas</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{conciliacionesCompletadas}</div>
            <p className="text-xs text-muted-foreground">Sin discrepancias</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pendientes</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{conciliacionesPendientes}</div>
            <p className="text-xs text-muted-foreground">Requieren revisión</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Discrepancias</CardTitle>
            <XCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{totalDiscrepancias}</div>
            <p className="text-xs text-muted-foreground">Por resolver</p>
          </CardContent>
        </Card>
      </div>

      {/* Upload Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Upload className="mr-2 h-5 w-5" /> Cargar Extracto Bancario
          </CardTitle>
          <CardDescription>Sube el archivo de extracto bancario para procesar la conciliación.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
            <Upload className="mx-auto h-12 w-12 text-gray-400" />
            <p className="mt-2 text-sm text-gray-600">
              Arrastra tu archivo de extracto bancario aquí
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Formatos soportados: Excel (.xlsx, .xls) o CSV (.csv)
            </p>
            <Button className="mt-4">
              <Upload className="mr-2 h-4 w-4" /> Seleccionar Archivo
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Conciliaciones List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            Historial de Conciliaciones
            <div className="flex space-x-2">
              <Button variant="outline" size="sm">
                <RefreshCw className="mr-2 h-4 w-4" /> Procesar Todas
              </Button>
              <Button variant="outline" size="sm">
                <ArrowDownToLine className="mr-2 h-4 w-4" /> Exportar
              </Button>
            </div>
          </CardTitle>
          <CardDescription>Lista de todas las conciliaciones procesadas.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4 mb-4">
            <Input
              placeholder="Buscar por banco, archivo o ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="max-w-sm"
              leftIcon={<Search className="h-4 w-4 text-gray-400" />}
            />
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-[180px]">
                <Filter className="mr-2 h-4 w-4 text-gray-400" />
                <SelectValue placeholder="Filtrar por estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Todos">Todos los estados</SelectItem>
                <SelectItem value="COMPLETADA">Completada</SelectItem>
                <SelectItem value="PENDIENTE">Pendiente</SelectItem>
                <SelectItem value="ERROR">Error</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Fecha</TableHead>
                <TableHead>Banco</TableHead>
                <TableHead>Archivo</TableHead>
                <TableHead>Registros</TableHead>
                <TableHead>Coincidencias</TableHead>
                <TableHead>Discrepancias</TableHead>
                <TableHead>Monto Total</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredConciliaciones.length > 0 ? (
                filteredConciliaciones.map((conc) => (
                  <TableRow key={conc.id}>
                    <TableCell className="font-medium">{conc.id}</TableCell>
                    <TableCell>{formatDate(conc.fecha)}</TableCell>
                    <TableCell>{conc.banco}</TableCell>
                    <TableCell className="max-w-[200px] truncate">{conc.archivo}</TableCell>
                    <TableCell>{conc.totalRegistros}</TableCell>
                    <TableCell className="text-green-600">{conc.coincidencias}</TableCell>
                    <TableCell className="text-red-600">{conc.discrepancias}</TableCell>
                    <TableCell>{formatCurrency(conc.montoTotal)}</TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          conc.estado === 'COMPLETADA'
                            ? 'success'
                            : conc.estado === 'PENDIENTE'
                              ? 'warning'
                              : 'destructive'
                        }
                      >
                        {conc.estado === 'COMPLETADA' && <CheckCircle className="h-3 w-3 mr-1" />}
                        {conc.estado === 'PENDIENTE' && <AlertTriangle className="h-3 w-3 mr-1" />}
                        {conc.estado === 'ERROR' && <XCircle className="h-3 w-3 mr-1" />}
                        {conc.estado}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedConciliacion(conc.id)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={10} className="text-center text-gray-500">
                    No se encontraron conciliaciones.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Discrepancias Detail */}
      {selectedConciliacion && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <AlertTriangle className="mr-2 h-5 w-5" /> Discrepancias - {selectedConciliacion}
            </CardTitle>
            <CardDescription>Detalle de discrepancias encontradas en la conciliación.</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Descripción</TableHead>
                  <TableHead>Monto Sistema</TableHead>
                  <TableHead>Monto Banco</TableHead>
                  <TableHead>Diferencia</TableHead>
                  <TableHead>Referencia</TableHead>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mockDiscrepancias
                  .filter((d) => d.conciliacionId === selectedConciliacion)
                  .map((disc) => (
                    <TableRow key={disc.id}>
                      <TableCell>
                        <Badge variant="outline">{disc.tipo.replace('_', ' ')}</Badge>
                      </TableCell>
                      <TableCell>{disc.descripcion}</TableCell>
                      <TableCell>{formatCurrency(disc.montoSistema)}</TableCell>
                      <TableCell>{formatCurrency(disc.montoBanco)}</TableCell>
                      <TableCell className={disc.diferencia > 0 ? 'text-green-600' : 'text-red-600'}>
                        {formatCurrency(disc.diferencia)}
                      </TableCell>
                      <TableCell>{disc.referencia}</TableCell>
                      <TableCell>{formatDate(disc.fecha)}</TableCell>
                      <TableCell>
                        <Badge
                          variant={disc.estado === 'RESUELTA' ? 'success' : 'warning'}
                        >
                          {disc.estado}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        {disc.estado === 'PENDIENTE' && (
                          <Button variant="outline" size="sm">
                            Resolver
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </motion.div>
  )
}
