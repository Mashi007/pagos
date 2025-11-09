import { useState, useEffect } from 'react'
import { Shield, Download, Search, Filter, Calendar, User, Activity, BarChart3, Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { auditoriaService, Auditoria as AuditoriaType, AuditoriaStats } from '@/services/auditoriaService'
import { toast } from 'sonner'

export function Auditoria() {
  const [auditorias, setAuditorias] = useState<AuditoriaType[]>([])
  const [stats, setStats] = useState<AuditoriaStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize] = useState(50)
  
  // Filtros
  const [filtros, setFiltros] = useState({
    usuario_email: '',
    modulo: 'ALL',
    accion: 'ALL',
    fecha_desde: '',
    fecha_hasta: '',
    ordenar_por: 'fecha',
    orden: 'desc'
  })

  // Cargar auditoría al montar el componente y auto-actualizar (polling cada 30 min)
  useEffect(() => {
    cargarAuditoria()
    cargarEstadisticas()

    const interval = setInterval(() => {
      cargarAuditoria()
      cargarEstadisticas()
    }, 30 * 60 * 1000) // 30 minutos

    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage, filtros.usuario_email, filtros.modulo, filtros.accion, filtros.fecha_desde, filtros.fecha_hasta])

  const cargarAuditoria = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const params = {
        skip: (currentPage - 1) * pageSize,
        limit: pageSize,
        usuario_email: filtros.usuario_email,
        modulo: filtros.modulo === 'ALL' ? '' : filtros.modulo,
        accion: filtros.accion === 'ALL' ? '' : filtros.accion,
        fecha_desde: filtros.fecha_desde || undefined,
        fecha_hasta: filtros.fecha_hasta || undefined,
        ordenar_por: filtros.ordenar_por,
        orden: filtros.orden
      }
      
      console.log('📡 Llamando a API: /api/v1/auditoria con params:', params)
      const response = await auditoriaService.listarAuditoria(params)
      console.log('✅ Respuesta API:', response)
      console.log('📊 Items recibidos:', response.items?.length || 0, 'Total:', response.total)
      
      if (response.items && response.items.length > 0) {
        setAuditorias(response.items)
        setTotal(response.total)
      } else {
        setAuditorias([])
        setTotal(response.total || 0)
        if (response.total === 0) {
          console.warn('⚠️ No hay registros de auditoría en la base de datos')
        }
      }
    } catch (err: any) {
      console.error('❌ Error API:', err)
      const errorMessage = err?.response?.data?.detail || err?.message || 'Error al cargar auditoría'
      setError(errorMessage)
      toast.error(`Error al cargar auditoría: ${errorMessage}`)
      setAuditorias([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }

  const cargarEstadisticas = async () => {
    try {
      const response = await auditoriaService.obtenerEstadisticas()
      setStats(response)
    } catch (err) {
      console.error('❌ Error cargando estadísticas:', err)
    }
  }

  const handleFiltrar = () => {
    setCurrentPage(1)
    cargarAuditoria()
  }

  const handleLimpiarFiltros = () => {
    setFiltros({
      usuario_email: '',
      modulo: 'ALL',
      accion: 'ALL',
      fecha_desde: '',
      fecha_hasta: '',
      ordenar_por: 'fecha',
      orden: 'desc'
    })
    setCurrentPage(1)
  }

  const handleExportarExcel = async () => {
    try {
      const paramsExport = {
        usuario_email: filtros.usuario_email || undefined,
        modulo: filtros.modulo === 'ALL' ? undefined : filtros.modulo,
        accion: filtros.accion === 'ALL' ? undefined : filtros.accion,
        fecha_desde: filtros.fecha_desde || undefined,
        fecha_hasta: filtros.fecha_hasta || undefined,
      }
      await auditoriaService.descargarExcel(paramsExport)
      toast.success('✅ Auditoría exportada exitosamente')
    } catch (err) {
      toast.error('❌ Error al exportar auditoría')
      console.error('Error:', err)
    }
  }

  const getAccionBadgeColor = (accion: string) => {
    const colors: any = {
      'CREAR': 'bg-green-600',
      'ACTUALIZAR': 'bg-blue-600',
      'ELIMINAR': 'bg-red-600',
      'LOGIN': 'bg-purple-600',
      'LOGOUT': 'bg-gray-600',
      'APROBAR': 'bg-green-600',
      'RECHAZAR': 'bg-red-600',
      'ACTIVAR': 'bg-green-600',
      'DESACTIVAR': 'bg-red-600',
    }
    return colors[accion] || 'bg-gray-600'
  }

  const getModuloBadgeColor = (modulo: string) => {
    const colors: any = {
      'USUARIOS': 'bg-red-600',
      'CLIENTES': 'bg-blue-600',
      'PRESTAMOS': 'bg-green-600',
      'PAGOS': 'bg-yellow-600',
      'AUDITORIA': 'bg-purple-600',
      'CONFIGURACION': 'bg-gray-600',
    }
    return colors[modulo] || 'bg-gray-600'
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Auditoría del Sistema</h1>
          <p className="text-gray-500 mt-1">
            Seguimiento completo de todas las acciones realizadas
          </p>
        </div>
        <Button onClick={handleExportarExcel} className="bg-green-600 hover:bg-green-700">
          <Download className="w-4 h-4 mr-2" />
          Exportar Excel
        </Button>
      </div>

      {/* Stats Dashboard */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Total Acciones</p>
                  <p className="text-2xl font-bold">{stats.total_acciones.toLocaleString()}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    Registros históricos
                  </p>
                </div>
                <Activity className="w-8 h-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Hoy</p>
                  <p className="text-2xl font-bold text-green-600">{stats.acciones_hoy}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    Acciones realizadas
                  </p>
                </div>
                <Calendar className="w-8 h-8 text-green-600" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Esta Semana</p>
                  <p className="text-2xl font-bold text-blue-600">{stats.acciones_esta_semana}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    Últimos 7 días
                  </p>
                </div>
                <BarChart3 className="w-8 h-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Este Mes</p>
                  <p className="text-2xl font-bold text-purple-600">{stats.acciones_este_mes}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    Últimos 30 días
                  </p>
                </div>
                <Shield className="w-8 h-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filtros */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Filter className="w-5 h-5 mr-2" />
            Filtros de Búsqueda
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className="block text-sm font-medium mb-1">Email Usuario</label>
              <Input
                placeholder="Buscar por email..."
                value={filtros.usuario_email}
                onChange={(e) => setFiltros({ ...filtros, usuario_email: e.target.value })}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Módulo</label>
              <Select value={filtros.modulo} onValueChange={(value) => setFiltros({ ...filtros, modulo: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar módulo" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">Todos los módulos</SelectItem>
                  <SelectItem value="USUARIOS">Usuarios</SelectItem>
                  <SelectItem value="CLIENTES">Clientes</SelectItem>
                  <SelectItem value="PRESTAMOS">Préstamos</SelectItem>
                  <SelectItem value="PAGOS">Pagos</SelectItem>
                  <SelectItem value="COBRANZAS">Cobranzas</SelectItem>
                  <SelectItem value="REPORTES">Reportes</SelectItem>
                  <SelectItem value="AUDITORIA">Auditoría</SelectItem>
                  <SelectItem value="CONFIGURACION">Configuración</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Acción</label>
              <Select value={filtros.accion} onValueChange={(value) => setFiltros({ ...filtros, accion: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar acción" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">Todas las acciones</SelectItem>
                  <SelectItem value="CREAR">Crear</SelectItem>
                  <SelectItem value="ACTUALIZAR">Actualizar</SelectItem>
                  <SelectItem value="ELIMINAR">Eliminar</SelectItem>
                  <SelectItem value="LOGIN">Login</SelectItem>
                  <SelectItem value="LOGOUT">Logout</SelectItem>
                  <SelectItem value="APROBAR">Aprobar</SelectItem>
                  <SelectItem value="RECHAZAR">Rechazar</SelectItem>
                  <SelectItem value="ACTIVAR">Activar</SelectItem>
                  <SelectItem value="DESACTIVAR">Desactivar</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          
          <div className="grid gap-4 md:grid-cols-2 mt-4">
            <div>
              <label className="block text-sm font-medium mb-1">Fecha Desde</label>
              <Input
                type="date"
                value={filtros.fecha_desde}
                onChange={(e) => setFiltros({ ...filtros, fecha_desde: e.target.value })}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Fecha Hasta</label>
              <Input
                type="date"
                value={filtros.fecha_hasta}
                onChange={(e) => setFiltros({ ...filtros, fecha_hasta: e.target.value })}
              />
            </div>
          </div>
          
          <div className="flex gap-2 mt-4">
            <Button onClick={handleFiltrar}>
              <Search className="w-4 h-4 mr-2" />
              Filtrar
            </Button>
            <Button variant="outline" onClick={handleLimpiarFiltros}>
              Limpiar Filtros
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Tabla */}
      <Card>
        <CardContent className="pt-6">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Email Usuario</TableHead>
                <TableHead>Acción</TableHead>
                <TableHead>Módulo</TableHead>
                <TableHead>Campo</TableHead>
                <TableHead>Descripción</TableHead>
                <TableHead>Resultado</TableHead>
                <TableHead>Fecha</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                    <p className="text-gray-500">Cargando auditoría...</p>
                  </TableCell>
                </TableRow>
              ) : error ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    <p className="text-red-500">{error}</p>
                    <Button onClick={cargarAuditoria} className="mt-2">
                      Reintentar
                    </Button>
                  </TableCell>
                </TableRow>
              ) : auditorias.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    <p className="text-gray-500">No se encontraron registros de auditoría</p>
                  </TableCell>
                </TableRow>
              ) : (
                auditorias.map((auditoria) => (
                  <TableRow key={auditoria.id}>
                    <TableCell>
                      <div className="flex items-center text-sm">
                        <User className="w-3 h-3 mr-1 text-gray-400" />
                        {auditoria.usuario_email || 'N/A'}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={getAccionBadgeColor(auditoria.accion)}>
                        {auditoria.accion}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getModuloBadgeColor(auditoria.modulo)}>
                        {auditoria.modulo}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-gray-600 font-medium">
                      {auditoria.campo || '-'}
                    </TableCell>
                    <TableCell className="text-sm text-gray-600 max-w-xs truncate">
                      {auditoria.descripcion || `${auditoria.accion} en ${auditoria.modulo}${auditoria.registro_id ? ` #${auditoria.registro_id}` : ''}`}
                    </TableCell>
                    <TableCell>
                      <Badge className={auditoria.resultado === 'EXITOSO' ? 'bg-green-600' : 'bg-red-600'}>
                        {auditoria.resultado}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-gray-600">
                      {new Date(auditoria.fecha).toLocaleString('es-VE', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
          
          {/* Paginación */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-gray-500">
                Mostrando {((currentPage - 1) * pageSize) + 1} a {Math.min(currentPage * pageSize, total)} de {total} registros
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(currentPage - 1)}
                  disabled={currentPage === 1}
                >
                  Anterior
                </Button>
                <span className="px-3 py-1 text-sm">
                  Página {currentPage} de {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(currentPage + 1)}
                  disabled={currentPage === totalPages}
                >
                  Siguiente
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}