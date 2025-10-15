import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Shield,
  Search,
  Filter,
  Calendar,
  User,
  Activity,
  Eye,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  FileText,
  RefreshCw,
  Download,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatDate } from '@/utils'

// Mock data para auditoría
const mockAuditoria = [
  {
    id: 'AUD001',
    usuario: 'itmaster@rapicreditca.com',
    accion: 'LOGIN',
    modulo: 'AUTH',
    descripcion: 'Inicio de sesión exitoso',
    ip: '192.168.1.100',
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    timestamp: '2024-07-20T10:30:00Z',
    resultado: 'EXITOSO',
    detalles: { metodo: 'POST', endpoint: '/api/v1/auth/login' },
  },
  {
    id: 'AUD002',
    usuario: 'carlos.mendoza@financiamiento.com',
    accion: 'CREATE',
    modulo: 'CLIENTES',
    descripcion: 'Cliente creado: Juan Pérez',
    ip: '192.168.1.101',
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    timestamp: '2024-07-20T10:25:00Z',
    resultado: 'EXITOSO',
    detalles: { cliente_id: 123, cedula: 'V12345678' },
  },
  {
    id: 'AUD003',
    usuario: 'maria.gonzalez@financiamiento.com',
    accion: 'UPDATE',
    modulo: 'PAGOS',
    descripcion: 'Pago actualizado: TRF789012',
    ip: '192.168.1.102',
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    timestamp: '2024-07-20T10:20:00Z',
    resultado: 'EXITOSO',
    detalles: { pago_id: 456, monto_anterior: 450.00, monto_nuevo: 500.00 },
  },
  {
    id: 'AUD004',
    usuario: 'luis.rodriguez@financiamiento.com',
    accion: 'DELETE',
    modulo: 'NOTIFICACIONES',
    descripcion: 'Notificación eliminada',
    ip: '192.168.1.103',
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    timestamp: '2024-07-20T10:15:00Z',
    resultado: 'FALLIDO',
    detalles: { error: 'Permisos insuficientes', notificacion_id: 789 },
  },
  {
    id: 'AUD005',
    usuario: 'itmaster@rapicreditca.com',
    accion: 'EXPORT',
    modulo: 'REPORTES',
    descripcion: 'Exportación de reporte de cartera',
    ip: '192.168.1.100',
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    timestamp: '2024-07-20T10:10:00Z',
    resultado: 'EXITOSO',
    detalles: { reporte_tipo: 'CARTERA', formato: 'PDF', registros: 150 },
  },
]

const modulos = [
  'AUTH', 'CLIENTES', 'PAGOS', 'PRESTAMOS', 'AMORTIZACION', 'REPORTES', 
  'APROBACIONES', 'AUDITORIA', 'CONFIGURACION', 'NOTIFICACIONES'
]

const acciones = [
  'LOGIN', 'LOGOUT', 'CREATE', 'READ', 'UPDATE', 'DELETE', 'EXPORT', 'IMPORT'
]

export function Auditoria() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterModulo, setFilterModulo] = useState('Todos')
  const [filterAccion, setFilterAccion] = useState('Todos')
  const [filterResultado, setFilterResultado] = useState('Todos')
  const [selectedAudit, setSelectedAudit] = useState<string | null>(null)

  const filteredAuditoria = mockAuditoria.filter((audit) => {
    const matchesSearch =
      audit.usuario.toLowerCase().includes(searchTerm.toLowerCase()) ||
      audit.descripcion.toLowerCase().includes(searchTerm.toLowerCase()) ||
      audit.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      audit.ip.includes(searchTerm)
    const matchesModulo = filterModulo === 'Todos' || audit.modulo === filterModulo
    const matchesAccion = filterAccion === 'Todos' || audit.accion === filterAccion
    const matchesResultado = filterResultado === 'Todos' || audit.resultado === filterResultado
    return matchesSearch && matchesModulo && matchesAccion && matchesResultado
  })

  const totalRegistros = mockAuditoria.length
  const exitosos = mockAuditoria.filter((a) => a.resultado === 'EXITOSO').length
  const fallidos = mockAuditoria.filter((a) => a.resultado === 'FALLIDO').length
  const usuariosActivos = new Set(mockAuditoria.map(a => a.usuario)).size

  const getAccionIcon = (accion: string) => {
    switch (accion) {
      case 'LOGIN': return <CheckCircle className="h-4 w-4 text-green-600" />
      case 'LOGOUT': return <XCircle className="h-4 w-4 text-gray-600" />
      case 'CREATE': return <FileText className="h-4 w-4 text-blue-600" />
      case 'UPDATE': return <RefreshCw className="h-4 w-4 text-yellow-600" />
      case 'DELETE': return <XCircle className="h-4 w-4 text-red-600" />
      case 'EXPORT': return <Download className="h-4 w-4 text-purple-600" />
      default: return <Activity className="h-4 w-4 text-gray-600" />
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <h1 className="text-3xl font-bold text-gray-900">Auditoría del Sistema</h1>
      <p className="text-gray-600">Monitorea todas las actividades y cambios realizados en el sistema.</p>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Registros</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalRegistros}</div>
            <p className="text-xs text-muted-foreground">Eventos registrados</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Exitosos</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{exitosos}</div>
            <p className="text-xs text-muted-foreground">Acciones completadas</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Fallidos</CardTitle>
            <XCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{fallidos}</div>
            <p className="text-xs text-muted-foreground">Errores detectados</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Usuarios Activos</CardTitle>
            <User className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{usuariosActivos}</div>
            <p className="text-xs text-muted-foreground">Usuarios únicos</p>
          </CardContent>
        </Card>
      </div>

      {/* Filtros y Búsqueda */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Filter className="mr-2 h-5 w-5" /> Filtros de Auditoría
          </CardTitle>
          <CardDescription>Filtra los registros de auditoría por diferentes criterios.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div>
              <label className="text-sm font-medium">Búsqueda</label>
              <Input
                placeholder="Usuario, descripción, IP..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                leftIcon={<Search className="h-4 w-4 text-gray-400" />}
              />
            </div>
            <div>
              <label className="text-sm font-medium">Módulo</label>
              <Select value={filterModulo} onValueChange={setFilterModulo}>
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar módulo" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Todos">Todos los módulos</SelectItem>
                  {modulos.map((modulo) => (
                    <SelectItem key={modulo} value={modulo}>{modulo}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium">Acción</label>
              <Select value={filterAccion} onValueChange={setFilterAccion}>
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar acción" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Todos">Todas las acciones</SelectItem>
                  {acciones.map((accion) => (
                    <SelectItem key={accion} value={accion}>{accion}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium">Resultado</label>
              <Select value={filterResultado} onValueChange={setFilterResultado}>
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar resultado" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Todos">Todos los resultados</SelectItem>
                  <SelectItem value="EXITOSO">Exitoso</SelectItem>
                  <SelectItem value="FALLIDO">Fallido</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabla de Auditoría */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            Registros de Auditoría
            <div className="flex space-x-2">
              <Button variant="outline" size="sm">
                <Download className="mr-2 h-4 w-4" /> Exportar
              </Button>
              <Button variant="outline" size="sm">
                <RefreshCw className="mr-2 h-4 w-4" /> Actualizar
              </Button>
            </div>
          </CardTitle>
          <CardDescription>Lista detallada de todas las actividades del sistema.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Usuario</TableHead>
                <TableHead>Acción</TableHead>
                <TableHead>Módulo</TableHead>
                <TableHead>Descripción</TableHead>
                <TableHead>IP</TableHead>
                <TableHead>Fecha/Hora</TableHead>
                <TableHead>Resultado</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAuditoria.length > 0 ? (
                filteredAuditoria.map((audit) => (
                  <TableRow key={audit.id}>
                    <TableCell className="font-medium">{audit.id}</TableCell>
                    <TableCell>
                      <div className="flex items-center">
                        <User className="h-4 w-4 mr-2 text-gray-400" />
                        <span className="text-sm">{audit.usuario}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center">
                        {getAccionIcon(audit.accion)}
                        <span className="ml-2">{audit.accion}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{audit.modulo}</Badge>
                    </TableCell>
                    <TableCell className="max-w-[200px] truncate">{audit.descripcion}</TableCell>
                    <TableCell className="font-mono text-sm">{audit.ip}</TableCell>
                    <TableCell>
                      <div className="text-sm">
                        {formatDate(audit.timestamp)}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={audit.resultado === 'EXITOSO' ? 'success' : 'destructive'}
                      >
                        {audit.resultado === 'EXITOSO' ? (
                          <>
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Exitoso
                          </>
                        ) : (
                          <>
                            <XCircle className="h-3 w-3 mr-1" />
                            Fallido
                          </>
                        )}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedAudit(audit.id)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={9} className="text-center text-gray-500">
                    No se encontraron registros de auditoría.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Detalle de Auditoría */}
      {selectedAudit && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Shield className="mr-2 h-5 w-5" /> Detalle de Auditoría - {selectedAudit}
            </CardTitle>
            <CardDescription>Información completa del evento de auditoría.</CardDescription>
          </CardHeader>
          <CardContent>
            {(() => {
              const audit = mockAuditoria.find(a => a.id === selectedAudit)
              if (!audit) return null

              return (
                <div className="grid gap-6 md:grid-cols-2">
                  <div className="space-y-4">
                    <h3 className="font-semibold">Información General</h3>
                    <div className="bg-gray-50 p-4 rounded-lg space-y-2">
                      <div><strong>ID:</strong> {audit.id}</div>
                      <div><strong>Usuario:</strong> {audit.usuario}</div>
                      <div><strong>Acción:</strong> {audit.accion}</div>
                      <div><strong>Módulo:</strong> {audit.modulo}</div>
                      <div><strong>Descripción:</strong> {audit.descripcion}</div>
                      <div><strong>Resultado:</strong> 
                        <Badge
                          variant={audit.resultado === 'EXITOSO' ? 'success' : 'destructive'}
                          className="ml-2"
                        >
                          {audit.resultado}
                        </Badge>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h3 className="font-semibold">Información Técnica</h3>
                    <div className="bg-gray-50 p-4 rounded-lg space-y-2">
                      <div><strong>IP:</strong> {audit.ip}</div>
                      <div><strong>Timestamp:</strong> {audit.timestamp}</div>
                      <div><strong>User Agent:</strong> 
                        <div className="text-xs text-gray-600 mt-1 break-all">
                          {audit.userAgent}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="md:col-span-2 space-y-4">
                    <h3 className="font-semibold">Detalles Adicionales</h3>
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                        {JSON.stringify(audit.detalles, null, 2)}
                      </pre>
                    </div>
                  </div>
                </div>
              )
            })()}
          </CardContent>
        </Card>
      )}
    </motion.div>
  )
}
